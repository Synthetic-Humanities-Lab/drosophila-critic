import io
import json
import wave

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from critic import server
from critic.performance import GROUPS, analyze_pair, decode_upload, run_comparison
from critic.performance_reading import ComparisonSummary


def wav(samples=None, rate=48000, channels=1):
    if samples is None:
        samples = np.sin(np.arange(rate) * 2 * np.pi * 200 / rate) * 0.1
    stream = io.BytesIO()
    with wave.open(stream, "wb") as file:
        file.setparams((channels, 2, rate, 0, "NONE", "not compressed"))
        file.writeframes(np.rint(samples * 32767).astype("<i2").tobytes())
    return stream.getvalue()


def test_decode_rejects_corrupt_silent_and_overlong_audio():
    for content in (b"not a WAV", wav(np.zeros(48000)), wav()[:-20]):
        with pytest.raises(ValueError):
            decode_upload(content)
    content = bytearray(wav())
    content[40:44] = (48000 * 121 * 2).to_bytes(4, "little")
    with pytest.raises(ValueError, match="120 seconds"):
        decode_upload(bytes(content))
    output, metadata = decode_upload(wav(rate=16000))
    assert len(output) == 48000
    assert metadata["resampling"] == "scipy.signal.resample_poly"


class DiagnosticRunner:
    """Test-only deterministic instrument, never used by the application."""

    def run(self, frames, directory, progress, seed, tail_seconds):
        phase = np.array(
            ["warmup"] * 25 + ["baseline"] * 50 + ["audio"] * len(frames) + ["tail"] * 150
        )
        amount = np.array([0] * 75 + [f["injected_voltage"] for f in frames] + [0] * 150)
        counts = np.tile(amount[:, None], (1, len(GROUPS))) + seed % 10
        type_counts = np.stack(
            [counts[phase == p].sum(axis=0) for p in ("baseline", "audio", "tail")]
        )
        return dict(
            group_names=list(GROUPS),
            group_sizes=[1] * len(GROUPS),
            group_counts=counts,
            phase=phase,
            before=75,
            type_names=np.array(GROUPS),
            type_sizes=np.ones(len(GROUPS)),
            phase_type_counts=type_counts,
            fly={"seed": seed, "weights_unchanged": True},
        )


def test_identical_input_null_provenance_and_interpretation_boundary(tmp_path):
    content = wav()
    result = run_comparison(
        {"a": content, "b": content},
        {"poem": "SECRET POEM", "label_a": "SECRET READER"},
        tmp_path,
        DiagnosticRunner(),
    )
    assert len(result["runs"]) == 16
    assert {r["fly"]["seed"] for r in result["runs"]} == {1101, 1102, 1103, 1104}
    assert all(row["rate"]["mean"] == 0 for row in result["response"]["differences"])
    assert all(row["temporal_separation_rms"] == 0 for row in result["response"]["differences"])
    assert "same measured downstream trace" in result["reading"]["text"]
    assert "SECRET" not in (tmp_path / "reading-input.json").read_text()
    with pytest.raises(ValidationError):
        ComparisonSummary.model_validate({**result["reading"]["input_summary"], "poem": "secret"})
    samples, _ = decode_upload((tmp_path / "a.wav").read_bytes())
    frames = json.loads((tmp_path / "encoding.json").read_text())["frames"]["a"]
    assert np.isclose(frames[0]["rms"], np.sqrt(np.mean(samples[:960] ** 2)))
    assert (tmp_path / "original-a.wav").read_bytes() == content


def test_temporal_comparison_does_not_pad_shorter_recording_with_silence():
    def measurement(length, value):
        return {
            **{
                m: np.full(4, value)
                for m in ("baseline", "raw_rate", "silence_rate", "rate", "tail")
            },
            "timeline": np.full((length + 40, 4), value),
            "raw_timeline": np.full((length + 40, 4), value),
            "audio_timeline": np.full((length, 4), value),
            "types": np.full(4, value),
        }

    result = analyze_pair(
        {"a": [measurement(10, 1)] * 4, "b": [measurement(20, 2)] * 4}, [1, 2], GROUPS
    )
    assert result["overlap_seconds"] == 1
    assert len(result["differences"][1]["paired_timeline_mean"]) == 10
    assert result["differences"][1]["temporal_separation_rms"] == 1


client = TestClient(server.app)


def request(token=None, **changes):
    metadata = {
        "poem": "Same poem",
        "label_a": "A",
        "label_b": "B",
        "same_poem_attested": True,
        **changes,
    }
    return client.post(
        "/api/comparisons",
        data={"metadata": json.dumps(metadata)},
        files={"a": ("a.wav", wav()), "b": ("b.wav", wav())},
        headers={"Authorization": token} if token else {},
    )


def test_upload_validation_and_shared_admission(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "RESULTS", tmp_path)
    monkeypatch.setattr(server, "active", None)
    assert request(same_poem_attested=False).status_code == 422
    assert request(poem=" ").status_code == 422
    assert request(unexpected="secret").status_code == 422
    captured = []
    monkeypatch.setattr(
        server.executor, "submit", lambda *args, **kwargs: captured.append((args, kwargs))
    )
    result = request()
    assert result.status_code == 202
    assert len(captured) == 1
    assert request().status_code == 409
    assert client.post("/api/readings", json={"poem": "test"}).status_code == 409
    assert client.get(f"/api/comparisons/{result.json()['id']}/a.wav").status_code == 404


def test_public_uploads_require_token_and_actual_body_is_bounded(monkeypatch):
    monkeypatch.setattr(server, "PUBLIC_MODE", True)
    monkeypatch.setattr(server, "UPLOAD_TOKEN", "")
    assert request().status_code == 503
    monkeypatch.setattr(server, "UPLOAD_TOKEN", "test-token")
    assert request().status_code == 401
    assert request(token="Bearer wrong").status_code == 401
    monkeypatch.setattr(server, "active", "busy")
    assert request(token="Bearer test-token").status_code == 409
    response = client.post("/api/readings", content=b"x" * 20001, headers={"Content-Length": "1"})
    assert response.status_code == 413


def test_raw_artifacts_are_allowlisted_and_expire(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "RESULTS", tmp_path)
    directory = tmp_path / "test-comparison"
    directory.mkdir()
    (directory / "result.json").write_text("{}")
    target = directory / "a-sound-1101"
    target.mkdir()
    (target / "provenance.json").write_text("{}")
    assert (
        client.get("/api/comparisons/test-comparison/a-sound-1101/provenance.json").status_code
        == 200
    )
    assert client.get("/api/comparisons/test-comparison/a-sound-1101/secret.txt").status_code == 404
    assert client.get("/api/comparisons/test-comparison/../test_api.py").status_code == 404


def test_display_text_cannot_change_response_or_interpretation(tmp_path):
    contents = {"a": wav(), "b": wav()}
    first = run_comparison(contents, {"poem": "One text"}, tmp_path / "one", DiagnosticRunner())
    second = run_comparison(
        contents, {"poem": "Entirely different words"}, tmp_path / "two", DiagnosticRunner()
    )
    assert first["poem_id"] != second["poem_id"]
    assert first["response"] == second["response"]
    assert first["reading"] == second["reading"]


def test_equal_rms_timing_change_reaches_encoder_and_analyzer(tmp_path):
    t = np.arange(48000) / 48000
    carrier = 0.1 * np.sin(2 * np.pi * 200 * t)
    a, b = carrier * (t < 0.5), carrier * (t >= 0.5)
    result = run_comparison(
        {"a": wav(a), "b": wav(b)}, {"poem": "Diagnostic fixture"}, tmp_path, DiagnosticRunner()
    )
    assert (
        abs(
            result["audio"]["a"]["normalization"]["output_rms"]
            - result["audio"]["b"]["normalization"]["output_rms"]
        )
        < 1e-6
    )
    assert result["response"]["differences"][1]["temporal_separation_rms"] > 0
    encoding = json.loads((tmp_path / "encoding.json").read_text())["frames"]
    assert encoding["a"] != encoding["b"]

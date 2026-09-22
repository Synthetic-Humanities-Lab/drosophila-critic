import numpy as np
import pytest

from critic.audio_encoder import encode
from critic.receiver.provisional import encode_provisional


def tone(f, seconds=0.5):
    return np.sqrt(2) * 0.05 * np.sin(2 * np.pi * f * np.arange(round(48000 * seconds)) / 48000)


def drive(f, quantity, strength=1):
    frames, meta = encode_provisional(tone(f), 48000, quantity, strength)
    return np.array([x["injected_voltage"] for x in frames]), meta


def test_frequency_contrast_and_common_reference():
    for q in ("displacement", "velocity", "legacy"):
        a, _ = drive(200, q)
        assert np.mean(a[5:24]) == pytest.approx(0.2, rel=0.001)
    a, _ = drive(800, "legacy")
    b, _ = drive(200, "legacy")
    np.testing.assert_allclose(a, b, atol=1e-12)
    for q in ("displacement", "velocity"):
        a, _ = drive(800, q)
        b, _ = drive(200, q)
        assert a[5:24].mean() < b[5:24].mean()


def test_silence_padding_and_legacy_identity():
    for q in ("displacement", "velocity", "legacy"):
        fs, m = encode_provisional(np.zeros(961), 48000, q, 2)
        assert len(fs) == 7 and m["sound_frames"] == 2
        assert not any(f["injected_voltage"] for f in fs)
    x = tone(200)
    fs, _ = encode_provisional(x, 48000, "legacy", 1)
    assert fs == encode(np.pad(x, (0, 4800)), 48000)


def test_gain_before_cap_and_fresh_state():
    a, _ = drive(200, "displacement", 1)
    b, _ = drive(200, "displacement", 2)
    np.testing.assert_allclose(b, a * 2)
    assert np.array_equal(a, drive(200, "displacement", 1)[0])
    c, m = drive(200, "displacement", 10)
    assert c.max() == 0.8 and m["capped_frames"] > 0


@pytest.mark.parametrize("strength", [0, -1, np.nan, np.inf])
def test_bad_gain(strength):
    with pytest.raises(ValueError):
        encode_provisional(tone(200), 48000, "displacement", strength)


def test_bad_quantity():
    with pytest.raises(ValueError):
        encode_provisional(tone(200), 48000, "fear", 1)


def test_analysis_subtracts_duration_matched_silence(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import scripts.receiver_sensitivity as pilot

    monkeypatch.setattr(pilot, "RAW", tmp_path)
    monkeypatch.setattr(pilot, "PUBLIC", tmp_path)
    monkeypatch.setattr(pilot, "SEEDS", [901])
    monkeypatch.setattr(pilot, "ARMS", [("legacy", 1.0)])
    (tmp_path / "PROTOCOL.md").write_text("fixture")
    conditions = {}
    for stimulus, audio_count in [("reference", 3), ("human", 5), ("tone200", 3), ("tone800", 5)]:
        for q in ("legacy", "displacement", "velocity"):
            key = f"{stimulus}-{q}-1"
            folder = tmp_path / f"{key}-901"
            folder.mkdir()
            # Warmup and baseline are excluded. Two sound frames, five decay,
            # one neural tail. Silent rate is 1 spike/frame per group.
            counts = np.array(
                [[99] * 3, [99] * 3] + [[audio_count] * 3] * 2 + [[1] * 3] * 5 + [[2] * 3]
            )
            phase = ["warmup", "baseline"] + ["audio"] * 7 + ["tail"]
            np.savez(
                folder / "populations.npz",
                group_names=pilot.GROUPS,
                group_counts=counts,
                phase=phase,
            )
            conditions[key] = ([{}] * 7, {"stimulus": stimulus, "sound_frames": 2})
        folder = tmp_path / f"{stimulus}-silence-901"
        folder.mkdir()
        np.savez(
            folder / "populations.npz",
            group_names=pilot.GROUPS,
            group_counts=np.ones((10, 3)),
            phase=phase,
        )
    for name in ("tone200-displacement-1", "repeat"):
        folder = tmp_path / f"{name}-901"
        folder.mkdir(exist_ok=True)
        np.savez(folder / "spikes.npz", neuron_indices=[2], offsets=[0, 1])
    runner = SimpleNamespace(groups={g: [1, 2] for g in pilot.GROUPS})
    result = pilot.analyze(conditions, runner, {})
    assert result["human_minus_reference"]["legacy-1"]["mean"] == [50] * 3
    assert result["conditions"]["reference-legacy-1"]["sound_hz_per_neuron"]["mean"] == [50] * 3
    assert result["conditions"]["reference-legacy-1"]["tail_hz_per_neuron"]["mean"] == [25] * 3
    assert result["repeat_exact_spikes"]

import json
import wave

import numpy as np
import pytest
from pydantic import ValidationError

from critic.audio_encoder import encode, preprocess, write_wav
from critic.interpretation import ResponseSummary, interpret
from critic.pipeline import validate_poem
from critic.tts import EspeakProvider


def test_silence_stays_silent_and_partial_frame_is_padded():
    pcm, meta = preprocess(np.zeros(442))
    frames = encode(pcm, 22050)
    assert meta["gain"] == 1
    assert len(frames) == 2 and frames[-1]["padded_samples"] == 440
    assert all(frame["injected_voltage"] == 0 for frame in frames)


def test_frame_rms_drives_voltage_without_text():
    pcm = np.repeat([0, 0.1, 0.2, 0.5], 441)
    frames = encode(pcm, 22050)
    assert [f["injected_voltage"] for f in frames] == pytest.approx([0, 0.4, 0.8, 0.8])
    assert [f["time"] for f in frames] == pytest.approx([0, 0.02, 0.04, 0.06])
    # A reversed waveform in each frame has the same transduction.
    reversed_frames = encode(pcm.reshape(-1, 441)[:, ::-1].ravel(), 22050)
    assert frames == reversed_frames


def test_encoder_matches_playback_pcm(tmp_path):
    pcm, meta = preprocess(np.sin(np.arange(1000) / 9) * 2)
    write_wav(tmp_path / "audio.wav", pcm, 22050)
    with wave.open(str(tmp_path / "audio.wav")) as wav:
        restored = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2") / 32768
    np.testing.assert_array_equal(pcm, restored)
    assert np.max(np.abs(pcm)) <= 0.95
    assert meta["output_rms"] == pytest.approx(0.1, abs=1e-4)
    with pytest.raises(ValueError):
        preprocess(np.array([np.nan]))


def summary(**updates):
    values = dict(
        duration=3,
        baseline_hz_per_neuron=3,
        deviation_hz_per_neuron=0.1,
        peak_time=2,
        peak_line=4,
        peak_delta_hz_per_neuron=1,
        transition_count=1,
        tail_delta_hz_per_neuron=0.2,
        recovery_seconds=None,
        tail_observed_seconds=1,
        threshold=0.1,
        populations=[],
    )
    return ResponseSummary(**(values | updates))


def test_interpreter_rejects_poem_and_handles_censored_recovery():
    with pytest.raises(ValidationError):
        summary(poem="secret poem")
    result = interpret(summary())
    assert "line 4" in result["text"]
    assert "closure remains unobserved" in result["text"]
    assert "poem" not in result["input_summary"]


def test_interpretation_does_not_invent_a_response():
    result = interpret(summary(peak_delta_hz_per_neuron=0, recovery_seconds=0))
    assert "stays close" in result["text"]
    assert "no sustained departure" in result["text"]
    assert "locomot" not in result["text"]


def test_tts_repeatable_and_different_poems_change_input(tmp_path):
    provider = EspeakProvider()
    signals = []
    for i, text in enumerate(
        [
            "The wind is passing through.",
            "The wind is passing through.",
            "A stone rests in the river.",
        ]
    ):
        directory = tmp_path / str(i)
        directory.mkdir()
        pcm, rate, lines, voice = provider.synthesize(text, directory)
        assert voice["voice"] == "en-us" and voice["rate_wpm"] == 165
        assert lines[0]["start"] == 0 and lines[0]["end"] > 0
        signals.append(encode(preprocess(pcm)[0], rate))
    assert signals[0] == signals[1]
    assert signals[0] != signals[2]


@pytest.mark.parametrize("text", ["", "  \n", "a" * 2001, "a\0b", "a\n" * 81, "\x01rate"])
def test_submission_limits(text):
    with pytest.raises(ValueError):
        validate_poem(text)


def test_saved_interpretation_contains_only_measurements():
    from critic.interpretation import summarize_response

    response = {
        "global": dict(
            audio_window_seconds=3,
            deviation_hz_per_neuron=0.1,
            peak_time=2,
            peak_perturbation_hz_per_neuron=1,
            tail_deviation_hz_per_neuron=0,
            recovery_seconds_after_audio_window=0,
            tail_observed_seconds=1,
        ),
        "baseline": {"hz_per_neuron": 3},
        "events": [{"kind": "peak perturbation", "line": 2, "poem": "NEVER_PASS_THIS"}],
        "populations": [],
        "measurement_rules": {"transition_band_hz_per_neuron": 0.1},
        "poem": "NEVER_PASS_THIS",
        "display": {"poem": "NEVER_PASS_THIS"},
    }
    assert "NEVER_PASS_THIS" not in json.dumps(summarize_response(response).model_dump())


def test_neural_voice_repeatability_timing_and_changed_acoustics(tmp_path):
    from critic.config import DATA
    from critic.neural_tts import MODEL_FILES, KokoroProvider

    if not all((DATA / "tts" / name).exists() for name in MODEL_FILES):
        pytest.skip("Run scripts/setup_voice.py for the fixed neural voice integration test")
    signals = []
    for i, text in enumerate(
        [
            "Who has seen the wind?\nNeither I nor you.",
            "Who has seen the wind?\nNeither I nor you.",
            "The stone is still.\nThe river passes.",
        ]
    ):
        directory = tmp_path / str(i)
        directory.mkdir()
        pcm, rate, lines, voice = KokoroProvider().synthesize(text, directory)
        assert rate == 24000 and voice["voice"] == "af_sarah"
        assert voice["speed"] == 1.0 and voice["model_sha256"] == MODEL_FILES
        assert lines[1]["start"] - lines[0]["end"] == pytest.approx(0.18)
        assert lines[-1]["end"] + 0.18 == pytest.approx(len(pcm) / rate)
        assert np.all(np.isfinite(pcm)) and np.any(pcm)
        signals.append(encode(preprocess(pcm)[0], rate))
    assert signals[0] == signals[1]
    assert signals[0] != signals[2]

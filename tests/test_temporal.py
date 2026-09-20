import numpy as np
import pytest
from pydantic import ValidationError

from critic.temporal import episodes, temporal_evidence
from critic.temporal_reading import AffectInput, interpret


def test_null_and_inconsistent_temporal_response():
    assert not temporal_evidence(np.zeros((8, 20)))["criterion_met"]
    opposed = np.ones((8, 20))
    opposed[4:] *= -1
    evidence = temporal_evidence(opposed)
    assert not evidence["criterion_met"]
    assert evidence["split_half_cosine"] == pytest.approx(-1)


def test_temporal_pattern_can_repeat_without_mean_rate_change():
    pattern = np.tile([1.0, -1.0], 20)
    x = np.array([pattern * gain for gain in np.linspace(0.95, 1.05, 8)])
    assert x.mean() == pytest.approx(0)
    evidence = temporal_evidence(x)
    assert evidence["criterion_met"]
    assert evidence["split_half_cosine"] == pytest.approx(1)


def test_episode_ranking_and_spacing():
    x = np.zeros((8, 50))
    x[:, 5:10] = 3
    x[:, 20:25] = -4
    x[:, 35:40] = 2
    selected = episodes(x)
    assert [e["start"] for e in selected] == [0.5, 2.0, 3.5]
    assert [e["mean"] for e in selected] == [3, -4, 2]
    assert selected[1]["negative"] == 8
    assert selected[0]["sd"] == 0
    assert episodes(np.zeros((8, 3))) == []


def test_interpretation_boundary_and_null_reading():
    fields = dict(
        seeds=8,
        temporal_criterion_met=False,
        descending_criterion_met=False,
        mean_rate_difference=0,
        tail_mean_difference=0,
        episodes=[],
    )
    summary = AffectInput(**fields)
    reading = interpret(summary)
    assert "does not meet" in reading["measurement"]
    assert "underdetermined" in reading["affect_reading"]
    assert reading["input_summary"] == fields
    with pytest.raises(ValidationError):
        AffectInput(**fields, poem="Little Fly")
    with pytest.raises(ValidationError):
        AffectInput(**fields, performer="Reader")


@pytest.mark.parametrize("tail", [0, -1, float("nan"), float("inf"), 0.031])
def test_tail_must_fit_the_simulation_clock(tail, tmp_path):
    from critic.simulation import SimulationRunner

    with pytest.raises(ValueError, match="Tail duration"):
        SimulationRunner.run(None, [{"injected_voltage": 0}], tmp_path, tail_seconds=tail)


def test_saved_local_pause_and_exact_dose_controls():
    import json
    from pathlib import Path

    from critic.audio_encoder import encode
    from critic.delivery import read_wav

    root = Path(__file__).resolve().parents[1]
    experiment = root / "experiments/temporal-v2"
    reference, rate = read_wav(root / "experiments/delivery-v1/reference/audio.wav")
    shifted, shifted_rate = read_wav(experiment / "localized-pause.wav")
    assert rate == shifted_rate
    np.testing.assert_array_equal(np.sort(reference), np.sort(shifted))
    assert not np.array_equal(reference, shifted)
    assert encode(shifted, rate) == json.loads((experiment / "localized-encoding.json").read_text())
    frames = json.loads((experiment / "reference-encoding.json").read_text())
    reversed_frames = json.loads((experiment / "frame_reverse-encoding.json").read_text())
    assert [f["injected_voltage"] for f in frames][::-1] == [
        f["injected_voltage"] for f in reversed_frames
    ]


def test_public_response_reconstructs_from_saved_counts():
    import json
    from pathlib import Path

    from critic.delivery import bin_rates

    root = Path(__file__).resolve().parents[1]
    folder = root / "experiments/temporal-v2"
    result = json.loads((folder / "confirmation.json").read_text())
    inventory = json.loads((root / "docs/population-inventory.json").read_text())
    name = "direct JON postsynaptic partners"
    size = inventory["groups"][name]["count"]
    with np.load(folder / "counts.npz") as archive:
        j = list(archive["group_names"]).index(name)
        paired = []
        for seed in result["manifest"]["seeds"]:
            curves = {}
            for condition in ["reference", "frame_reverse"]:
                counts = archive[f"{condition}_{seed}_group_counts"][:, j].astype(float)
                silence = archive[f"silence_1309_{seed}_group_counts"][:, j]
                curves[condition] = bin_rates((counts - silence)[75 : 75 + 1309], size)
            paired.append((curves["frame_reverse"] - curves["reference"])[:261])
    expected = result["comparisons"]["frame_reverse"]
    np.testing.assert_allclose(np.mean(paired, axis=0), expected["trace"]["mean"])
    actual = temporal_evidence(paired)
    for key, value in actual.items():
        assert value == pytest.approx(expected["populations"][name]["temporal"][key])


def test_roundoff_does_not_count_as_directional_evidence():
    from critic.temporal import paired_summary

    result = paired_summary([1e-16, -1e-16, 0, 1e-8, -1e-8])
    assert (result["positive"], result["negative"], result["zero"]) == (1, 1, 3)

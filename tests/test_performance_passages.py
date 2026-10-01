import numpy as np
import pytest
from pydantic import ValidationError

from critic.performance_passages import MatchedPassage, passage_report, validate_windows
from critic.performance_reading import ComparisonSummary, PassageDifference


def test_windows_reject_out_of_bounds_overlap_and_nonfinite_values():
    valid = [{"a": {"start": 0.0, "end": 1.0}, "b": {"start": 0.5, "end": 1.5}}]
    validate_windows(valid, {"a": 1.0, "b": 2.0})
    with pytest.raises(ValueError, match="inside"):
        validate_windows(valid, {"a": 0.5, "b": 2.0})
    with pytest.raises(ValueError, match="nonoverlapping"):
        validate_windows(valid * 2, {"a": 2.0, "b": 2.0})
    for start, end in ((float("nan"), 1.0), (0.0, float("inf")), (0.0, 0.1)):
        with pytest.raises(ValidationError):
            MatchedPassage.model_validate({"a": {"start": start, "end": end}, "b": valid[0]["b"]})


def fixture():
    # B's corresponding passage occurs a second later and has a different input.
    a, b = np.zeros((150, 1)), np.zeros((200, 1))
    a[25:75] = 1
    b[75:125] = 3
    measurements = {"a": [{"audio_rates": a}] * 4, "b": [{"audio_rates": b}] * 4}
    frames = {"a": [{"injected_voltage": 0.1}] * 150, "b": [{"injected_voltage": 0.2}] * 200}
    return measurements, frames


def test_native_clock_means_exposure_and_boundary_sensitivity():
    measurements, frames = fixture()
    windows = [{"a": {"start": 0.5, "end": 1.5}, "b": {"start": 1.5, "end": 2.5}}]
    result = passage_report(measurements, frames, windows, {"a": 3, "b": 4}, ["test"])
    row = result["passages"][0]
    assert row["populations"][0]["difference"]["values"] == [2.0] * 4
    assert row["valid_boundary_combinations"] == 81
    assert row["populations"][0]["same_direction_across_seeds_and_boundaries"]
    assert row["performances"]["b"]["net_spikes_per_neuron_by_seed"] == [[3.0]] * 4
    assert row["performances"]["b"]["integrated_drive"] == pytest.approx(0.2)


def test_identical_input_cannot_be_differentiated_by_arbitrary_annotations():
    measurements, frames = fixture()
    frames["b"] = frames["a"]
    with pytest.raises(ValueError, match="different cuts alone"):
        passage_report(
            measurements,
            frames,
            [{"a": {"start": 0.5, "end": 1.5}, "b": {"start": 1.0, "end": 2.0}}],
            {"a": 3, "b": 4},
            ["test"],
        )


def test_passage_summary_does_not_accept_poem_or_reader_names():
    value = dict(
        number=1,
        durations=[1.0, 2.0],
        mean_drives=[0.1, 0.2],
        direct_rate_difference=0.1,
        seed_differences=[0.1, 0.2],
        boundary_direction_consistent=False,
    )
    with pytest.raises(ValidationError):
        PassageDifference.model_validate({**value, "poem": "secret"})
    with pytest.raises(ValidationError):
        ComparisonSummary.model_validate(
            {
                "durations": [1.0, 2.0],
                "seeds": [1, 2],
                "differences": [],
                "passages": [{**value, "reader": "secret"}],
            }
        )

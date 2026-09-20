import copy

import numpy as np
import pytest
from pydantic import ValidationError
from test_response import count_record

from critic.benchmark import compare
from critic.interpretation import interpret_control, summarize_control


def paired_record():
    r = count_record()
    r["fly"].update(seed=64, runtime_weights_sha256="fixed", configuration={"noise_hz": 1.2})
    return r


def test_identical_trajectories_have_no_sound_effect_despite_baseline_change():
    r = paired_record()
    b = compare(r, copy.deepcopy(r), [])
    assert b["global"]["poem_hz_per_neuron"] == 25
    assert b["global"]["delta_hz_per_neuron"] == 0
    assert all(p["delta_hz_per_neuron"] == 0 for p in b["populations"])
    assert all(t["delta_hz_per_neuron"] == 0 for t in b["timeline"])
    assert "indistinguishable" in interpret_control(summarize_control(b))["text"]


def test_control_subtraction_casts_unsigned_counts_and_ranks_actual_difference():
    r = paired_record()
    quiet = copy.deepcopy(r)
    quiet["counts"] = np.zeros_like(r["counts"])
    quiet["phase_type_counts"] = np.zeros_like(r["phase_type_counts"])
    quiet["group_counts"] = np.zeros_like(r["group_counts"])
    b = compare(quiet, r, [])
    assert b["global"]["delta_hz_per_neuron"] == -25
    assert b["populations"][0]["name"] == "A"
    assert b["populations"][0]["delta_hz_per_neuron"] == -40
    summary = summarize_control(b)
    with pytest.raises(ValidationError):
        type(summary)(**summary.model_dump(), poem="Forbidden text")


@pytest.mark.parametrize("change", ["seed", "pre_stimulus", "clock"])
def test_mismatched_controls_are_rejected(change):
    r = paired_record()
    control = copy.deepcopy(r)
    if change == "seed":
        control["fly"]["seed"] = 65
    elif change == "pre_stimulus":
        control["counts"][0] += 1
    else:
        control["phase"][75] = "tail"
    with pytest.raises(ValueError):
        compare(r, control, [])

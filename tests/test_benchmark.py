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


def test_functional_reading_keeps_roles_separate_and_counts_spikes():
    b = compare(paired_record(), paired_record(), [])
    b["monitored_populations"] = [
        dict(
            name="DNp01",
            neurons=2,
            available=True,
            audio_hz_per_neuron=6.0,
            silence_hz_per_neuron=1.0,
            delta_hz_per_neuron=5.0,
        )
    ]
    reading = interpret_control(summarize_control(b))
    note = reading["functional_notes"][0]
    assert note["net_spikes_vs_silence"] == 2
    assert note["label"] == "Escape take-off circuit"
    assert "not evidence of fear" in note["limit"]
    assert reading["input_summary"]["circuits"][0]["name"] == "DNp01"


def test_unknown_cell_type_has_no_invented_behavioral_meaning():
    b = compare(paired_record(), paired_record(), [])
    b["monitored_populations"] = [
        dict(
            name="unmapped",
            neurons=2,
            available=True,
            audio_hz_per_neuron=10.0,
            silence_hz_per_neuron=0.0,
            delta_hz_per_neuron=10.0,
        )
    ]
    assert interpret_control(summarize_control(b))["functional_notes"] == []


def test_affect_lens_uses_the_same_text_blind_summary_and_respects_null_effect():
    b = compare(paired_record(), paired_record(), [])
    s = summarize_control(b)
    reading = interpret_control(s)
    assert "no global separation" in reading["affect"]["text"]
    assert "not an affect detector" in reading["affect"]["scope"]
    assert reading["input_summary"] == s.model_dump()
    assert "poem" not in reading["input_summary"]


def test_published_performances_have_distinct_coupled_evidence():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    a = json.loads((root / "examples/blake-the-fly/result.json").read_text())
    b = json.loads((root / "examples/blake-sayers/result.json").read_text())
    assert a["poem_id"] == b["poem_id"]
    assert a["audio"]["sha256"] != b["audio"]["sha256"]
    assert a["audio"]["duration"] != b["audio"]["duration"]
    assert a["timeline"] != b["timeline"]
    for result in (a, b):
        assert result["reading"]["input_summary"]["duration"] == result["benchmark"]["duration"]
        assert result["benchmark"]["pre_stimulus_identical"]
        assert result["reading"]["affect"]["provider"] == "response-only-affect-lens-v1"

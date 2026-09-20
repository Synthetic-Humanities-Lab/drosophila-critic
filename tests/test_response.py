"""Known spike-count examples test measurement arithmetic, never runtime fallbacks."""

import numpy as np
import pytest

from critic.response import analyze


def count_record(persistent=False):
    phase = np.array(["warmup"] * 25 + ["baseline"] * 50 + ["audio"] * 10 + ["tail"] * 50)
    per_type = np.zeros((len(phase), 2), dtype=np.uint32)
    per_type[phase == "audio"] = [10, 40]
    if persistent:
        per_type[phase == "tail"] = [10, 40]
    return {
        "fly": {"neurons": 100},
        "phase": phase,
        "before": 75,
        "counts": per_type.sum(axis=1),
        "type_names": np.array(["B", "A"]),
        "type_sizes": np.array([50, 50]),
        "phase_type_counts": np.array(
            [per_type[phase == p].sum(axis=0) for p in ("baseline", "audio", "tail")]
        ),
        "group_names": ["known group", "missing group"],
        "group_sizes": [50, 0],
        "group_counts": np.column_stack([per_type[:, 1], np.zeros(len(phase), dtype=np.uint32)]),
        "type_counts": per_type.reshape(-1, 5, 2).sum(axis=1),
    }


def test_rates_peaks_recovery_rank_and_missing_annotation():
    frames = [{"rms": 0.1, "injected_voltage": 0.4}] * 10
    response, timeline, _, populations = analyze(
        count_record(), frames, [{"line": 7, "start": 0, "end": 0.2}]
    )
    assert response["baseline"]["hz_per_neuron"] == 0
    assert response["global"]["during_hz_per_neuron"] == 25
    assert response["global"]["peak_time"] == pytest.approx(0.08)
    assert response["global"]["recovery_seconds_after_audio_window"] == pytest.approx(0.08)
    assert response["populations"][0]["name"] == "A"
    assert response["populations"][0]["delta_hz_per_neuron"] == 40
    assert populations[0]["name"] == "A"
    assert response["monitored_populations"][1]["available"] is False
    assert timeline[75]["line"] == 7
    assert any(e.get("state") == "above baseline band" for e in response["events"])


def test_recovery_is_censored_when_tail_never_returns():
    response, *_ = analyze(
        count_record(persistent=True), [{"rms": 0, "injected_voltage": 0}] * 10, []
    )
    assert response["global"]["recovery_seconds_after_audio_window"] is None
    assert response["global"]["recovery_censored"] is True

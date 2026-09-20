import numpy as np
import pytest
from pydantic import ValidationError

from critic.audio_encoder import encode
from critic.history import GAPS, factorial, stimuli, summarize
from critic.history_reading import GapSummary, HistorySummary, interpret


def test_identical_probe_equal_dose_and_matched_clock():
    rate = 1000
    source = np.sin(np.arange(8000) * 0.071) * np.linspace(0.01, 0.15, 8000)
    trials = stimuli(source, rate)
    for gap in GAPS:
        prefix = f"g{round(gap * 1000)}"
        ap, aq, bp, bq = [
            trials[f"{prefix}_{h}_{e}"]
            for h, e in (("a", "probe"), ("a", "quiet"), ("b", "probe"), ("b", "quiet"))
        ]
        start = round((6 + gap) * rate)
        assert len(ap[0]) == len(aq[0]) == len(bp[0]) == len(bq[0])
        np.testing.assert_array_equal(ap[0][start:], bp[0][start:])
        np.testing.assert_array_equal(ap[0][:start], aq[0][:start])
        np.testing.assert_array_equal(bp[0][:start], bq[0][:start])
        assert not np.any(aq[0][start:]) and not np.any(bq[0][start:])
        np.testing.assert_array_equal(np.sort(ap[0][:6000]), np.sort(bp[0][:6000]))
        drives = [
            [f["injected_voltage"] for f in encode(trial[0], rate)[:300]] for trial in [ap, bp]
        ]
        assert sorted(drives[0]) == sorted(drives[1])
        assert drives[0] != drives[1]


def test_lingering_activity_is_not_changed_probe_reception():
    counts = [np.full((8, 100), n, dtype=np.uint32) for n in [15, 10, 25, 20]]
    result = factorial(*counts)
    assert np.all(result["total"] == 10)
    assert np.all(result["lingering"] == 10)
    assert np.all(result["after_a"] == 5)
    assert np.all(result["interaction"] == 0)
    counts[2][:] = 22
    assert np.all(factorial(*counts)["interaction"] == -3)
    with pytest.raises(ValueError, match="shape"):
        factorial(np.zeros(2), np.zeros(3), np.zeros(2), np.zeros(2))


def test_fixed_windows_do_not_promote_late_effect_to_primary():
    rates = np.zeros((8, 20))
    rates[:, 10:] = 1
    report = summarize(rates)
    assert not report["early"]["temporal"]["criterion_met"]
    assert report["full"]["temporal"]["criterion_met"]
    with pytest.raises(ValueError):
        summarize(np.ones((4, 20)))


def test_interpreter_requires_response_only_and_preserves_null():
    gap = dict(
        gap_seconds=0,
        early_interaction=False,
        full_interaction=False,
        early_lingering=True,
        full_lingering=False,
        probe_after_a=True,
        probe_after_b=True,
        full_probe_after_a=True,
        full_probe_after_b=True,
        descending_interaction=False,
        early_mean=0,
    )
    summary = HistorySummary(seeds=8, gaps=[GapSummary(**gap)])
    reading = interpret(summary)
    assert "Neither" in reading["response"]
    assert "distinguishable continuation" in reading["reading"]
    with pytest.raises(ValidationError):
        HistorySummary(seeds=8, gaps=[], poem="Little Fly")
    with pytest.raises(ValidationError):
        GapSummary(**gap, reader="Someone")
    gap["early_interaction"] = True
    assert (
        "already differently affected"
        in interpret(HistorySummary(seeds=8, gaps=[GapSummary(**gap)]))["reading"]
    )


def test_published_interaction_reconstructs_from_counts():
    import json
    from pathlib import Path

    from critic.delivery import bin_rates

    root = Path(__file__).resolve().parents[1]
    folder = root / "experiments/history-v3"
    report = json.loads((folder / "comparison.json").read_text())
    inventory = json.loads((root / "docs/population-inventory.json").read_text())
    group = "direct JON postsynaptic partners"
    size = inventory["groups"][group]["count"]
    with np.load(folder / "counts.npz") as archive:
        column = list(archive["group_names"]).index(group)
        for gap in GAPS:
            prefix = f"g{round(gap * 1000)}"
            start = 75 + round((6 + gap) / 0.02)
            rates = []
            for seed in report["manifest"]["seeds"]:
                counts = [
                    archive[f"{prefix}_{h}_{e}_{seed}_group_counts"][
                        start : start + 100, column
                    ].astype(np.int64)
                    for h, e in (("a", "probe"), ("a", "quiet"), ("b", "probe"), ("b", "quiet"))
                ]
                ap, aq, bp, bq = counts
                rates.append(bin_rates(bp - bq - ap + aq, size))
            expected = report["gaps"][str(gap)]["populations"][group]["interaction"]
            np.testing.assert_allclose(rates, expected["trace"]["seeds"])
            actual = summarize(rates)
            for window in ["early", "full"]:
                for section in ["mean", "temporal"]:
                    for key, value in actual[window][section].items():
                        other = expected[window][section][key]
                        if isinstance(value, (bool, int)) or value is None:
                            assert value == other
                        else:
                            # BLAS reduction roundoff differs between ARM/macOS and x86/Linux.
                            np.testing.assert_allclose(value, other, rtol=1e-12, atol=1e-12)
            for key, value in actual["trace"].items():
                np.testing.assert_allclose(value, expected["trace"][key], rtol=1e-12, atol=1e-12)

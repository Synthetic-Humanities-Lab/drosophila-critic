import numpy as np
import pytest
from pydantic import ValidationError

from critic.emphasis import variants
from critic.emphasis_reading import Summary, Window, interpret


def test_energy_balance_off_target_and_smooth_gain():
    rate = 1000
    x = np.rint(np.sin(np.arange(6000) * 0.09) * 0.1 * 32768) / 32768
    result = variants(x, rate, [(1, 2), (4, 5)])
    outside = np.ones(len(x), bool)
    outside[1000:2000] = False
    outside[4000:5000] = False
    for y, gain in result.values():
        np.testing.assert_array_equal(y[outside], x[outside])
        assert abs(np.sqrt(np.mean(y * y)) - np.sqrt(np.mean(x * x))) < 1e-6
        assert gain.min() >= np.sqrt(0.55) - 1e-12 and gain.max() <= np.sqrt(1.45) + 1e-12
        assert gain[1000] == gain[1999] == gain[4000] == gain[4999] == 1
        assert np.max(np.abs(np.diff(gain))) < 0.02
    assert not np.array_equal(result["earlier"][0], result["later"][0])


def test_interpretation_excludes_text_and_retains_null():
    fields = dict(
        windows=[Window(start=1, end=2, mean=0.01, criterion=False)],
        descending_criterion=False,
        whole_mean=0,
        off_target_mean=0,
    )
    assert "Neither" in interpret(Summary(**fields))["response"]
    with pytest.raises(ValidationError):
        Summary(**fields, poem="The Fly")
    with pytest.raises(ValueError):
        variants(np.ones(1000) * 0.1, 1000, [(0, 0.05), (0.1, 0.5)])


def test_published_local_metrics_reconstruct_from_counts():
    import json
    from pathlib import Path

    from critic.delivery import bin_rates
    from critic.temporal import temporal_evidence

    root = Path(__file__).resolve().parents[1]
    folder = root / "experiments/emphasis-v4"
    r = json.loads((folder / "comparison.json").read_text())
    inventory = json.loads((root / "docs/population-inventory.json").read_text())
    group = "direct JON postsynaptic partners"
    size = inventory["groups"][group]["count"]
    with np.load(folder / "counts.npz") as archive:
        j = list(archive["group_names"]).index(group)
        for w in r["comparisons"]["earlier_later"][group]["windows"]:
            start = 75 + round(w["start"] / 0.02)
            end = 75 + round(w["end"] / 0.02)
            rates = []
            for seed in r["manifest"]["seeds"]:
                diff = archive[f"earlier_{seed}_group_counts"][start:end, j].astype(
                    np.int64
                ) - archive[f"later_{seed}_group_counts"][start:end, j].astype(np.int64)
                rates.append(bin_rates(diff, size))
            t = temporal_evidence(rates)
            assert t["criterion_met"] == w["temporal"]["criterion_met"]
            for key in ["mean_trace_rms", "seed_sd_rms", "split_half_cosine"]:
                assert t[key] == pytest.approx(w["temporal"][key], abs=1e-12)
            np.testing.assert_allclose(np.mean(rates, axis=1), w["mean"]["values"], atol=1e-12)

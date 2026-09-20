import numpy as np

from critic.audio_encoder import encode
from critic.delivery import bin_rates, equalize, paired_stats, variants


def example():
    rate = 1000
    speech = [np.sin(np.arange(100) * 0.1) * 0.2, np.cos(np.arange(100) * 0.2) * 0.15]
    x = np.concatenate([speech[0], np.zeros(20), speech[1], np.zeros(20)])
    lines = [dict(line=1, start=0, end=0.1), dict(line=2, start=0.12, end=0.22)]
    return x, rate, lines


def test_diagnostic_pauses_and_order_preserve_samples_energy_duration():
    x, rate, lines = example()
    modified = variants(x, rate, lines)
    for name in ["pauses", "reordered"]:
        y, timing = modified[name]
        np.testing.assert_array_equal(np.sort(x), np.sort(y))
        for line in timing:
            old = next(row for row in lines if row["line"] == line["line"])
            np.testing.assert_array_equal(
                y[round(line["start"] * rate) : round(line["end"] * rate)],
                x[round(old["start"] * rate) : round(old["end"] * rate)],
            )
        assert not np.array_equal(x, y)
    assert modified["pauses"][1][1]["start"] == 0.1


def test_normalization_and_identical_input_boundary():
    x, rate, lines = example()
    waves = {"reference": x, "quiet": x * 0.02, "emphasis": variants(x, rate, lines)["emphasis"][0]}
    normalized, meta = equalize(waves)
    levels = [m["output_rms"] for m in meta.values()]
    assert max(levels) - min(levels) < 2e-6
    assert all(m["output_peak"] <= 0.95 for m in meta.values())
    a = encode(normalized["reference"], rate)
    b = encode(-normalized["reference"], rate)
    assert a == b
    assert [f["injected_voltage"] for f in a] != [
        f["injected_voltage"] for f in encode(normalized["emphasis"], rate)
    ]


def test_paired_statistics_and_rates():
    s = paired_stats([-1, 0, 1])
    assert s["mean"] == 0 and s["sd"] == 1
    assert s["positive"] == s["negative"] == s["zero"] == 1
    np.testing.assert_allclose(bin_rates(np.full((10, 2), 2), [2, 4]), [[50, 25], [50, 25]])


def test_published_rates_derive_from_saved_counts():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "experiments/delivery-v1"
    result = json.loads((root / "comparison.json").read_text())
    assert len(result["seeds"]) == 8
    assert len(result["exact_controls"]) == 16
    assert all(c["spikes_identical"] for c in result["exact_controls"])
    with np.load(root / "counts.npz") as data:
        groups = list(data["group_names"])
        for name, c in result["manifest"]["conditions"].items():
            assert abs(c["normalization"]["output_rms"] - 0.05) < 3e-6
            for i, seed in enumerate(result["seeds"]):
                control = f"silence_{c['frames']}_{seed}"
                counts = data[f"{name}_{seed}_group_counts"].astype(float)
                silence = data[f"{control}_group_counts"].astype(float)
                j = groups.index("direct JON postsynaptic partners")
                before = 75
                expected = (
                    (counts - silence)[before : before + c["frames"], j] / (1017 * 0.02)
                ).mean()
                assert np.isclose(expected, result["metrics"][name][i]["mean"][2])
                np.testing.assert_array_equal(counts[:before], silence[:before])
                if name in ["repeat", "polarity"]:
                    np.testing.assert_array_equal(counts, data[f"reference_{seed}_group_counts"])

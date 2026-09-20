"""Run real-connectome controls and a public-domain poem. No fixtures/fake neural data."""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from critic.audio_encoder import encode  # noqa: E402
from critic.config import DT, RESULTS, ROOT  # noqa: E402
from critic.pipeline import EXAMPLE, run_reading, save_json  # noqa: E402
from critic.response import analyze  # noqa: E402
from critic.simulation import SimulationRunner  # noqa: E402


def main():
    runner = SimulationRunner()
    save_json(ROOT / "docs" / "population-inventory.json", runner.inventory())
    signals = {
        "validation-silence": np.zeros(44100),
        "validation-pulse": np.r_[np.zeros(11025), np.ones(22050) * 0.2, np.zeros(11025)],
    }
    records, summaries = {}, {}
    for name, signal in signals.items():
        directory = RESULTS / name
        directory.mkdir(exist_ok=True)
        frames = encode(signal, 22050)
        record = runner.run(frames, directory)
        records[name] = record
        response, *_ = analyze(record, frames, [])
        summaries[name] = response
        save_json(directory / "response.json", response)
        with np.load(directory / "spikes.npz") as spikes:
            np.testing.assert_array_equal(np.diff(spikes["offsets"]), record["counts"])
        expected_mean = record["counts"][record["phase"] == "audio"].mean() / (runner.brain.n * DT)
        assert np.isclose(expected_mean, response["global"]["during_hz_per_neuron"])
    silence, pulse = records.values()
    np.testing.assert_array_equal(
        silence["counts"][: silence["before"]], pulse["counts"][: pulse["before"]]
    )
    changed = np.count_nonzero(silence["group_counts"][:, 1] != pulse["group_counts"][:, 1])
    assert changed > 0, "Stimulation failed to propagate beyond injected JONs"
    repeat_dir = RESULTS / "validation-repeat"
    repeat_dir.mkdir(exist_ok=True)
    repeat = runner.run(encode(signals["validation-silence"], 22050), repeat_dir)
    np.testing.assert_array_equal(silence["counts"], repeat["counts"])
    np.testing.assert_array_equal(silence["group_counts"], repeat["group_counts"])
    poem = run_reading(EXAMPLE, RESULTS / "blake-the-fly", runner)
    assert len(poem["timeline"]) > 100
    assert any(p["delta_hz_per_neuron"] != 0 for p in poem["response"]["populations"])
    assert "Little fly" not in json.dumps(poem["reading"]["input_summary"])
    with np.load(RESULTS / "blake-the-fly" / "spikes.npz") as spikes:
        np.testing.assert_array_equal(
            np.diff(spikes["offsets"]), [row["spike_count"] for row in poem["timeline"]]
        )
    report = {
        "passed": True,
        "neural_fixture": False,
        "upstream_commit": poem["fly"]["upstream_commit"],
        "neurons": runner.brain.n,
        "connections": len(runner.brain.weights),
        "input_neurons": len(runner.ear),
        "same_seed_repeat_exact_counts": True,
        "weights_unchanged": poem["fly"]["weights_unchanged"],
        "raw_spikes_reconcile_with_reported_counts": True,
        "silence_baseline_hz_per_neuron": summaries["validation-silence"]["baseline"][
            "hz_per_neuron"
        ],
        "pulse_vs_silence_changed_downstream_frames": int(changed),
        "silence_downstream": summaries["validation-silence"]["monitored_populations"][1],
        "pulse_downstream": summaries["validation-pulse"]["monitored_populations"][1],
        "poem": {
            "title": "The Fly",
            "author": "William Blake",
            "source": "https://poets.org/poem/fly",
            "public_domain": True,
            "audio_seconds": poem["audio"]["duration"],
            "global": poem["response"]["global"],
        },
        "limits": "One seed; pulse causal comparison does not calibrate speech hearing or validate behavior.",
    }
    save_json(ROOT / "docs" / "validation.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

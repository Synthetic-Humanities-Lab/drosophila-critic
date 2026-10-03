"""Compare browser response hashes with the saved original Python poem runs."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()


def main():
    directory = ROOT / "experiments/browser-v2"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=directory / "benchmark-release.json")
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    display = json.loads((ROOT / "experiments/encounter-v2/display-neurons.json").read_text())
    lookup = np.full(166700, -1, np.int32)
    lookup[display["neuron_indices"]] = np.arange(len(display["neuron_indices"]))
    comparisons = []
    for run in report["results"]:
        key = {"Robot": "a", "Human": "b"}[run["label"]]
        source = ROOT / f"results/encounter-v1/{key}-sound-{run['seed']}-g1"
        with np.load(source / "populations.npz") as populations:
            indices = [list(populations["group_names"]).index(g) for g in run["group_names"]]
            expected = {
                "counts": digest(populations["global_counts"].tolist()),
                "groups": digest(populations["group_counts"][:, indices].tolist()),
            }
        with np.load(source / "spikes.npz") as spikes:
            offsets = spikes["offsets"]
            neurons = spikes["neuron_indices"]
            bins = []
            for start in range(0, len(offsets) - 1, 5):
                end = min(start + 5, len(offsets) - 1)
                sampled = lookup[neurons[int(offsets[start]) : int(offsets[end])]]
                bins.append(np.unique(sampled[sampled >= 0]).tolist())
            expected["spatial"] = digest(bins)
        matches = {k: value == run["response_sha256"][k] for k, value in expected.items()}
        comparisons.append(
            {
                "label": run["label"],
                "python_source": str(source.relative_to(ROOT)),
                "steps": run["recorded_steps"],
                "bins": len(bins),
                "python_sha256": expected,
                "exact": matches,
            }
        )
    passed = len(comparisons) == 2 and all(all(c["exact"].values()) for c in comparisons)
    result = {
        "schema_version": "browser-capture-parity-v1",
        "source": args.report.name,
        "comparison": "All timestep global/group counts and all sampled spike bins, including final partial bin",
        "exact": passed,
        "results": comparisons,
    }
    (directory / "capture-parity.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not passed:
        raise SystemExit("Browser response capture does not match saved Python runs")


if __name__ == "__main__":
    main()

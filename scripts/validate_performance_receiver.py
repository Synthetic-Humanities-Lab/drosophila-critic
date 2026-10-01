"""Local numerical validation; generates diagnostic tones, uploads no recordings."""

import argparse
from pathlib import Path

import numpy as np

from critic.audio_encoder import encode
from critic.performance import GROUPS, RATE, SEEDS, TAIL_SECONDS, analyze_pair, measure
from critic.pipeline import save_json
from critic.simulation import SimulationRunner


def validate(directory):
    directory.mkdir(parents=True, exist_ok=False)
    runner = SimulationRunner()
    time = np.arange(RATE * 2) / RATE
    wave = 0.12 * np.sin(2 * np.pi * 200 * time) * ((time > 0.5) & (time < 1.5))
    frames = encode(wave, RATE)
    silent = [{"injected_voltage": 0.0} for _ in frames]
    measurements = {"a": [], "b": []}
    checks, provenance = [], []
    for seed in SEEDS:
        records = {}
        for condition, stimulus in (("silence", silent), ("pulse", frames), ("repeat", frames)):
            target = directory / f"{condition}-{seed}"
            target.mkdir()
            records[condition] = runner.run(stimulus, target, seed=seed, tail_seconds=TAIL_SECONDS)
            provenance.append(records[condition]["fly"])
        a, b, control = records["pulse"], records["repeat"], records["silence"]
        exact = all(
            np.array_equal(a[key], b[key]) for key in ("counts", "group_counts", "type_counts")
        )
        measurements["a"].append(measure(a, control))
        measurements["b"].append(measure(b, control))
        downstream = measurements["a"][-1]["rate"][1]
        checks.append(
            {
                "seed": seed,
                "identical_input_exact_repeat": exact,
                "direct_downstream_change_from_silence": float(downstream),
            }
        )
        print(checks[-1], flush=True)
    response = analyze_pair(measurements, [2.0, 2.0], records["pulse"]["type_names"])
    report = {"checks": checks, "groups": list(GROUPS), "response": response, "runs": provenance}
    save_json(directory / "validation.json", report)
    assert all(row["identical_input_exact_repeat"] for row in checks)
    assert all(row["direct_downstream_change_from_silence"] > 0 for row in checks)
    assert all(
        row["rate"]["mean"] == 0 and row["temporal_separation_rms"] == 0
        for row in response["differences"]
    )
    assert all(row["weights_unchanged"] for row in provenance)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    validate(parser.parse_args().output)

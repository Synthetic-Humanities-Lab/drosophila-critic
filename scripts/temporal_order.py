"""Equal-drive temporal organization diagnostic at the neural input boundary."""

import json
import time

import numpy as np

from critic.config import DT, ROOT
from critic.simulation import SimulationRunner, sha256
from scripts.receiver_sensitivity import describe, digest

PUBLIC = ROOT / "experiments/receiver-v2/order"
RAW = ROOT / "results/receiver-order"
SEEDS = [1001, 1002, 1003, 1004]
GROUPS = ["JO-A/B input", "direct JON postsynaptic partners", "descending_neuron"]


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(",", ":")))


def stimuli(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or len(x) < 10 or not np.all(np.isfinite(x)) or np.any((x < 0) | (x > 0.8)):
        raise ValueError("Need at least ten finite injected values between zero and 0.8")
    blocks = np.arange(len(x) // 10 * 10).reshape(-1, 10)
    remainder = np.arange(blocks.size, len(x))
    orders = {
        "original": np.arange(len(x)),
        "reverse": np.concatenate([blocks[::-1].ravel(), remainder]),
        "shuffle": np.concatenate(
            [blocks[np.random.default_rng(20260922).permutation(len(blocks))].ravel(), remainder]
        ),
    }
    waves = {k: x[order] for k, order in orders.items()}
    waves.update(constant=np.full_like(x, x.mean()), silence=np.zeros_like(x))
    return waves, orders


def temporal_summary(differences):
    d = np.asarray(differences)
    mean = d.mean(axis=0)
    signal = np.sqrt(np.mean(mean**2, axis=0))
    error = np.sqrt(np.mean((d.std(axis=0, ddof=1) / np.sqrt(len(d))) ** 2, axis=0))
    cosines = []
    for i, row in enumerate(d):
        others = (d.sum(axis=0) - row) / (len(d) - 1)
        denominator = np.linalg.norm(row, axis=0) * np.linalg.norm(others, axis=0)
        cosines.append(
            [float(a / b) if b else None for a, b in zip(np.sum(row * others, axis=0), denominator)]
        )
    return {
        "rms_mean_difference": signal.tolist(),
        "rms_standard_error": error.tolist(),
        "descriptive_ratio": [float(a / b) if b else None for a, b in zip(signal, error)],
        "leave_one_seed_out_cosine": cosines,
        "difference_trace": describe(d),
    }


def main():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    source = ROOT / "experiments/receiver-v2/sensitivity/inputs.json"
    original = json.loads(source.read_text())["reference-displacement-1"]
    waves, orders = stimuli([f["injected_voltage"] for f in original["frames"]])
    n = len(waves["original"])
    frames = {k: [{"injected_voltage": float(v)} for v in x] for k, x in waves.items()}
    save(
        PUBLIC / "inputs.json",
        {
            "source_sha256": sha256(source),
            "source_condition": "reference-displacement-1",
            "dt": DT,
            "values": {k: x.tolist() for k, x in waves.items()},
            "source_frame_at_output_frame": {k: x.tolist() for k, x in orders.items()},
        },
    )
    runner = SimulationRunner()
    records, counts = {}, {}
    sizes = np.array([len(runner.groups[g]) for g in GROUPS])
    for name in [*waves, "repeat"]:
        for seed in SEEDS[:1] if name == "repeat" else SEEDS:
            fs = frames["original" if name == "repeat" else name]
            folder = RAW / f"{name}-{seed}"
            folder.mkdir(parents=True, exist_ok=True)
            key = {
                "input": digest(fs),
                "seed": seed,
                "protocol": sha256(PUBLIC / "PROTOCOL.md"),
                "sources": {
                    p: sha256(ROOT / p)
                    for p in [
                        "scripts/temporal_order.py",
                        "scripts/receiver_sensitivity.py",
                        "critic/simulation.py",
                    ]
                },
                "upstream": runner.source_hashes,
                "data": runner.data_hashes,
            }
            if (folder / "run.json").exists():
                record = json.loads((folder / "run.json").read_text())
                if record["key"] != key or any(
                    sha256(folder / f) != h for f, h in record["artifacts"].items()
                ):
                    raise ValueError(f"Stale or corrupt run: {folder}")
            else:
                started = time.monotonic()
                response = runner.run(fs, folder, seed=seed)
                record = {
                    "key": key,
                    "fly": response["fly"],
                    "runtime_seconds": time.monotonic() - started,
                    "artifacts": {f: sha256(folder / f) for f in ["spikes.npz", "populations.npz"]},
                }
                save(folder / "run.json", record)
                print(name, seed, round(record["runtime_seconds"], 2), flush=True)
            records[f"{name}-{seed}"] = record
            with np.load(folder / "populations.npz") as data:
                start = np.flatnonzero(data["phase"] == "audio")[0]
                indices = [data["group_names"].tolist().index(g) for g in GROUPS]
                counts[name, seed] = (
                    data["group_counts"][start:, indices].astype(float) / DT / sizes
                )
    with (
        np.load(RAW / "original-1001/spikes.npz") as a,
        np.load(RAW / "repeat-1001/spikes.npz") as b,
    ):
        exact = all(np.array_equal(a[k], b[k]) for k in a.files)
    if not exact:
        raise RuntimeError("Repeat failed exact spike identity check")

    def bins(x):
        return np.array([x[i : i + 5].mean(axis=0) for i in range(0, len(x), 5)])

    corrected = {k: np.array([counts[k, s] - counts["silence", s] for s in SEEDS]) for k in waves}
    conditions = {}
    for name, rows in corrected.items():
        conditions[name] = {
            "mean_rate": describe(rows[:, :n].mean(axis=1)),
            "tail_rate": describe(rows[:, n:].mean(axis=1)),
            "trace": describe([bins(row) for row in rows]),
            "input_mean": float(waves[name].mean()),
            "input_sum": float(waves[name].sum()),
            "input_rms": float(np.sqrt(np.mean(waves[name] ** 2))),
            "capped_frames": int(np.sum(waves[name] >= 0.8)),
        }
    comparisons = {}
    for name in ["reverse", "shuffle", "constant"]:
        delta = corrected[name] - corrected["original"]
        comparison = {
            "mean_rate_difference": describe(delta[:, :n].mean(axis=1)),
            "tail_rate_difference": describe(delta[:, n:].mean(axis=1)),
            "native_time": temporal_summary([bins(row[:n]) for row in delta]),
        }
        if name in orders:
            inverse = np.argsort(orders[name])
            aligned = corrected[name][:, :n][:, inverse] - corrected["original"][:, :n]
            comparison["same_blocks_different_context"] = temporal_summary(
                [bins(row) for row in aligned]
            )
        comparisons[name] = comparison
    save(
        PUBLIC / "comparison.json",
        {
            "status": "diagnostic input-order pilot; no new oral performance or physiological calibration",
            "production_changed": False,
            "reading": None,
            "seeds": SEEDS,
            "groups": GROUPS,
            "group_sizes": sizes.tolist(),
            "input_duration_seconds": n * DT,
            "tail_seconds": 1,
            "repeat_exact_spikes": exact,
            "conditions": conditions,
            "comparisons": comparisons,
            "runs": records,
        },
    )
    print("Complete", flush=True)


if __name__ == "__main__":
    main()

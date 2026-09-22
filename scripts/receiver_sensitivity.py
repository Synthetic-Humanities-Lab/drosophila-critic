"""Run the preregistered provisional adapter pilot through original FlyBrain."""

import hashlib
import json
import time

import numpy as np
from scipy.io import wavfile

from critic.config import DT, ROOT
from critic.receiver.provisional import encode_provisional
from critic.simulation import SimulationRunner, sha256

PUBLIC = ROOT / "experiments/receiver-v2/sensitivity"
RAW = ROOT / "results/receiver-sensitivity"
SEEDS = [901, 902, 903, 904]
GROUPS = ["JO-A/B input", "direct JON postsynaptic partners", "descending_neuron"]
ARMS = [("legacy", 1.0)] + [(q, g) for q in ("displacement", "velocity") for g in (0.5, 1.0, 2.0)]


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, indent=2))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def prepare():
    conditions = {}
    for name in ("reference", "human", "tone200", "tone800"):
        if name.startswith("tone"):
            rate = 48000
            samples = np.sqrt(2) * 0.05 * np.sin(2 * np.pi * int(name[4:]) * np.arange(rate) / rate)
            source_hash = hashlib.sha256(samples.tobytes()).hexdigest()
        else:
            source = ROOT / f"experiments/delivery-v1/{name}/audio.wav"
            rate, pcm = wavfile.read(source)
            assert pcm.dtype == np.int16
            samples = pcm.astype(float) / 32768
            source_hash = sha256(source)
        for quantity, strength in ARMS:
            if name.startswith("tone") and strength != 1:
                continue
            frames, metadata = encode_provisional(samples, rate, quantity, strength)
            key = f"{name}-{quantity}-{strength:g}"
            metadata.update(source_sha256=source_hash, duration=len(samples) / rate, stimulus=name)
            conditions[key] = (frames, metadata)
        frames, metadata = encode_provisional(np.zeros_like(samples), rate, "legacy", 1)
        conditions[f"{name}-silence"] = (frames, metadata)
    return conditions


def run(runner, key, frames, seed):
    folder = RAW / f"{key}-{seed}"
    folder.mkdir(parents=True, exist_ok=True)
    identity = {
        "input": digest(frames),
        "seed": seed,
        "protocol": sha256(PUBLIC / "PROTOCOL.md"),
        "sources": {
            str(p.relative_to(ROOT)): sha256(p)
            for p in [
                ROOT / "scripts/receiver_sensitivity.py",
                ROOT / "critic/receiver/provisional.py",
                ROOT / "critic/receiver/healthy.py",
                ROOT / "critic/receiver/acoustics.py",
                ROOT / "critic/audio_encoder.py",
                ROOT / "critic/simulation.py",
            ]
        },
        "upstream": runner.source_hashes,
        "data": runner.data_hashes,
    }
    if (folder / "run.json").exists():
        record = json.loads((folder / "run.json").read_text())
        if record["identity"] != identity:
            raise ValueError(f"Stale cache: {folder}")
        for name, checksum in record["artifacts"].items():
            if sha256(folder / name) != checksum:
                raise ValueError(f"Corrupt cache: {folder / name}")
        return record
    start = time.monotonic()
    response = runner.run(frames, folder, seed=seed)
    record = {
        "identity": identity,
        "fly": response["fly"],
        "runtime_seconds": time.monotonic() - start,
        "artifacts": {n: sha256(folder / n) for n in ("spikes.npz", "populations.npz")},
    }
    save(folder / "run.json", record)
    print(key, seed, round(record["runtime_seconds"], 2), flush=True)
    return record


def rates(key, seed, sound_frames):
    with np.load(RAW / f"{key}-{seed}/populations.npz") as data:
        names = data["group_names"].tolist()
        counts = data["group_counts"][:, [names.index(g) for g in GROUPS]].astype(float)
        phase = data["phase"]
        start = np.flatnonzero(phase == "audio")[0]
        return counts[start:] / DT, (phase[start:] == "tail"), sound_frames


def describe(values):
    a = np.asarray(values)
    return {
        "per_seed": a.tolist(),
        "mean": a.mean(axis=0).tolist(),
        "min": a.min(axis=0).tolist(),
        "max": a.max(axis=0).tolist(),
    }


def analyze(conditions, runner, records):
    sizes = np.array([len(runner.groups[g]) for g in GROUPS])
    results = {}
    for key, (frames, meta) in conditions.items():
        if key.endswith("silence"):
            continue
        name = meta["stimulus"]
        means, tails, traces = [], [], []
        for seed in SEEDS:
            counts, tail, n = rates(key, seed, meta["sound_frames"])
            control, _, _ = rates(f"{name}-silence", seed, n)
            delta = (counts - control) / sizes
            means.append(delta[:n].mean(axis=0))
            tails.append(delta[tail].mean(axis=0))
            # Retain final partial bin without dropping it or diluting its rate.
            traces.append(
                np.array([delta[i : i + 5].mean(axis=0) for i in range(0, len(delta), 5)])
            )
        results[key] = {
            "metadata": meta,
            "input_sha256": digest(frames),
            "sound_hz_per_neuron": describe(means),
            "tail_hz_per_neuron": describe(tails),
            "trace_100ms": describe(traces),
            "time_seconds": (np.arange(len(traces[0])) * 0.1).tolist(),
        }
    comparisons = {}
    for q, g in ARMS:
        a = results[f"human-{q}-{g:g}"]["sound_hz_per_neuron"]["per_seed"]
        b = results[f"reference-{q}-{g:g}"]["sound_hz_per_neuron"]["per_seed"]
        comparisons[f"{q}-{g:g}"] = describe(np.array(a) - b)
    tones = {}
    for q in ("legacy", "displacement", "velocity"):
        a = results[f"tone800-{q}-1"]["sound_hz_per_neuron"]["per_seed"]
        b = results[f"tone200-{q}-1"]["sound_hz_per_neuron"]["per_seed"]
        tones[q] = describe(np.array(a) - b)
    with (
        np.load(RAW / "tone200-displacement-1-901/spikes.npz") as a,
        np.load(RAW / "repeat-901/spikes.npz") as b,
    ):
        repeat_exact = all(np.array_equal(a[k], b[k]) for k in a.files)
    if not repeat_exact:
        raise RuntimeError("Identical seeded input failed exact spike reproducibility")
    return {
        "status": "provisional engineering sensitivity pilot; not physiological calibration",
        "production_changed": False,
        "reading": None,
        "seeds": SEEDS,
        "groups": GROUPS,
        "group_sizes": sizes.tolist(),
        "repeat_exact_spikes": repeat_exact,
        "protocol_sha256": sha256(PUBLIC / "PROTOCOL.md"),
        "conditions": results,
        "human_minus_reference": comparisons,
        "tone800_minus_200": tones,
        "runs": records,
        "limits": [
            "Four seeds describe this pilot only; not biological replicates or confidence intervals",
            "20 ms neural envelope input cannot represent carrier phase locking",
            "Same scalar drive to all legacy JO-A/B; no validated subtype tuning",
            "Linear mechanical model extrapolated to speech and beyond source measurement band",
            "Mechanical state decay occupies five input frames before the separate neural tail",
            "Whole-recording rate contrast does not align passages and does not control exposure duration",
        ],
    }


def main():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    conditions = prepare()
    # Archive the entire injection trajectory before simulating.
    save(
        PUBLIC / "inputs.json",
        {k: {"frames": f, "metadata": m} for k, (f, m) in conditions.items()},
    )
    runner = SimulationRunner()
    records = {}
    # Small diagnostic runs first; report runtimes before the longer poem pilot.
    keys = sorted(conditions, key=lambda k: (not k.startswith("tone"), k))
    for key in keys:
        for seed in SEEDS:
            records[f"{key}-{seed}"] = run(runner, key, conditions[key][0], seed)
    records["repeat-901"] = run(runner, "repeat", conditions["tone200-displacement-1"][0], 901)
    report = analyze(conditions, runner, records)
    save(PUBLIC / "comparison.json", report)
    print("Saved", PUBLIC / "comparison.json", flush=True)


if __name__ == "__main__":
    main()

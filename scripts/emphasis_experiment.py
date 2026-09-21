"""Local emphasis experiment using the original frozen simulation adapter."""

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from critic.audio_encoder import encode, write_wav
from critic.config import DT, ROOT
from critic.delivery import bin_rates, read_wav
from critic.emphasis import variants
from critic.emphasis_reading import Summary, Window, interpret
from critic.simulation import SimulationRunner, sha256
from critic.temporal import paired_summary, temporal_evidence

PUBLIC = ROOT / "experiments/emphasis-v4"
ARCHIVE = ROOT / "results/emphasis-v4"
SEEDS = list(range(301, 309))
GROUPS = ["direct JON postsynaptic partners", "descending_neuron", "JO-A/B input"]


def save(path, data):
    path.write_text(json.dumps(data, allow_nan=False, separators=(",", ":")))


def digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()


def prepare():
    old = json.loads((ROOT / "experiments/delivery-v1/manifest.json").read_text())
    lines = old["conditions"]["reference"]["lines"]
    targets = [next(line for line in lines if line["line"] == n) for n in [2, 17]]
    source = ROOT / "experiments/delivery-v1/reference/audio.wav"
    x, rate = read_wav(source)
    waves = {
        "reference": (x, np.ones(len(x))),
        **variants(x, rate, [(line["start"], line["end"]) for line in targets]),
        "silence": (np.zeros_like(x), np.ones(len(x))),
    }
    frames = {}
    conditions = {}
    gains = {}
    for name, (y, gain) in waves.items():
        folder = PUBLIC / name
        folder.mkdir(parents=True, exist_ok=True)
        write_wav(folder / "audio.wav", y, rate)
        saved, sr = read_wav(folder / "audio.wav")
        if sr != rate or not np.array_equal(saved, y):
            raise ValueError("PCM mismatch")
        frames[name] = encode(y, rate)
        save(folder / "encoding.json", frames[name])
        conditions[name] = dict(
            input_sha256=digest(frames[name]),
            audio_sha256=sha256(folder / "audio.wav"),
            duration=len(y) / rate,
            rms=float(np.sqrt(np.mean(y * y))),
            peak=float(np.max(np.abs(y))),
            gain_min=float(gain.min()),
            gain_max=float(gain.max()),
            integrated_drive=sum(f["injected_voltage"] for f in frames[name]) * DT,
            capped_frames=sum(f["injected_voltage"] >= 0.8 for f in frames[name]),
        )
        gains[name] = gain
    np.savez_compressed(PUBLIC / "gain-envelopes.npz", **gains, sample_rate=rate)
    manifest = dict(
        seeds=SEEDS,
        targets=targets,
        lines=lines,
        conditions=conditions,
        source_sha256=sha256(source),
        protocol_sha256=sha256(PUBLIC / "PROTOCOL.md"),
        dt=DT,
        before_steps=75,
        tail_steps=50,
    )
    save(PUBLIC / "manifest.json", manifest)
    return frames, manifest


def run(runner, name, seed, fs, manifest):
    folder = ARCHIVE / f"{name}-{seed}"
    folder.mkdir(parents=True, exist_ok=True)
    key = dict(
        seed=seed,
        input=digest(fs),
        protocol=manifest["protocol_sha256"],
        adapter=sha256(ROOT / "critic/simulation.py"),
        upstream=runner.source_hashes,
        data=runner.data_hashes,
    )
    if (folder / "run.json").exists():
        if json.loads((folder / "run.json").read_text())["key"] != key:
            raise ValueError("Cache mismatch")
        return
    start = time.perf_counter()
    r = runner.run(fs, folder, seed=seed)
    save(
        folder / "run.json",
        dict(
            key=key,
            fly=r["fly"],
            seconds=time.perf_counter() - start,
            counts_sha256=sha256(folder / "populations.npz"),
            spikes_sha256=sha256(folder / "spikes.npz"),
        ),
    )
    print(name, seed, round(time.perf_counter() - start, 2), flush=True)


def analyze(frames, manifest):
    inventory = json.loads((ROOT / "docs/population-inventory.json").read_text())
    sizes = np.array([inventory["groups"][g]["count"] for g in GROUPS])
    counts = {}
    evidence = {}
    provenance = {}
    signature = None
    n = len(frames["reference"])
    for name in frames:
        counts[name] = []
        provenance[name] = []
        for seed in SEEDS:
            folder = ARCHIVE / f"{name}-{seed}"
            meta = json.loads((folder / "run.json").read_text())
            fly = meta["fly"]
            if (
                meta["key"]["input"] != digest(frames[name])
                or meta["key"]["protocol"] != manifest["protocol_sha256"]
                or fly["seed"] != seed
                or not fly["weights_unchanged"]
                or fly["data_sha256"] != inventory["data_sha256"]
            ):
                raise ValueError("Provenance mismatch")
            sig = {
                k: fly[k]
                for k in ["configuration", "runtime_weights_sha256", "source_sha256", "environment"]
            }
            if signature is None:
                signature = sig
            if signature != sig:
                raise ValueError("Model configuration differs")
            for file, key in [
                ("populations.npz", "counts_sha256"),
                ("spikes.npz", "spikes_sha256"),
            ]:
                if sha256(folder / file) != meta[key]:
                    raise ValueError("Artifact changed")
            provenance[name].append(meta)
            with np.load(folder / "populations.npz") as p:
                idx = [list(p["group_names"]).index(g) for g in GROUPS]
                counts[name].append(p["group_counts"][75 : 75 + n, idx].astype(np.int64))
                for key in ["group_counts", "global_counts", "phase_counts", "type_sizes"]:
                    evidence[f"{name}_{seed}_{key}"] = p[key]
                evidence["group_names"] = p["group_names"]
                evidence["type_names"] = p["type_names"]
            if name in ["earlier", "later"]:
                with (
                    np.load(folder / "spikes.npz") as a,
                    np.load(ARCHIVE / f"reference-{seed}" / "spikes.npz") as b,
                ):
                    stop = 75 + int(manifest["targets"][0]["start"] / DT)
                    if not np.array_equal(
                        a["offsets"][: stop + 1], b["offsets"][: stop + 1]
                    ) or not np.array_equal(
                        a["neuron_indices"][: a["offsets"][stop]],
                        b["neuron_indices"][: b["offsets"][stop]],
                    ):
                        raise ValueError("Pre-target trajectories differ")
        counts[name] = np.array(counts[name])
    timeline = {}
    for name in ["reference", "earlier", "later"]:
        rates = np.array([bin_rates(c, sizes) for c in counts[name] - counts["silence"]])
        timeline[name] = {
            g: dict(
                mean=rates[:, :, j].mean(axis=0).tolist(),
                low=rates[:, :, j].min(axis=0).tolist(),
                high=rates[:, :, j].max(axis=0).tolist(),
            )
            for j, g in enumerate(GROUPS)
        }
    comparisons = {}
    off = np.ones(n, dtype=bool)
    for t in manifest["targets"]:
        off[round(t["start"] / DT) : round((t["end"] + 0.3) / DT)] = False
    for label, a, b in [
        ("earlier_reference", "earlier", "reference"),
        ("later_reference", "later", "reference"),
        ("earlier_later", "earlier", "later"),
    ]:
        diff = counts[a] - counts[b]
        populations = {}
        for j, g in enumerate(GROUPS):
            windows = []
            for t in manifest["targets"]:
                start = round(t["start"] / DT)
                end = round((t["end"] + 0.3) / DT)
                end = start + (end - start) // 5 * 5
                rates = np.array([bin_rates(c[start:end, j], sizes[j]) for c in diff])
                windows.append(
                    dict(
                        line=t["line"],
                        start=start * DT,
                        end=end * DT,
                        temporal=temporal_evidence(rates),
                        mean=paired_summary(rates.mean(axis=1)),
                    )
                )
            populations[g] = dict(
                windows=windows,
                whole=paired_summary(diff[:, :, j].mean(axis=1) / (sizes[j] * DT)),
                off_target=paired_summary(diff[:, off, j].mean(axis=1) / (sizes[j] * DT)),
            )
        comparisons[label] = populations
    summaries = {
        label: Summary(
            windows=[
                Window(
                    start=w["start"],
                    end=w["end"],
                    mean=w["mean"]["mean"],
                    criterion=w["temporal"]["criterion_met"],
                )
                for w in c[GROUPS[0]]["windows"]
            ],
            descending_criterion=any(
                w["temporal"]["criterion_met"] for w in c[GROUPS[1]]["windows"]
            ),
            whole_mean=c[GROUPS[0]]["whole"]["mean"],
            off_target_mean=c[GROUPS[0]]["off_target"]["mean"],
        )
        for label, c in comparisons.items()
    }
    readings = {label: interpret(summary) for label, summary in summaries.items()}
    save(
        PUBLIC / "interpretation-input.json",
        {label: s.model_dump() for label, s in summaries.items()},
    )
    np.savez_compressed(PUBLIC / "counts.npz", **evidence)
    result = dict(
        manifest=manifest,
        groups=GROUPS,
        timeline=timeline,
        comparisons=comparisons,
        readings=readings,
        provenance=provenance,
        counts_sha256=sha256(PUBLIC / "counts.npz"),
        source_sha256={
            str(p.relative_to(ROOT)): sha256(p)
            for p in [
                Path(__file__).resolve(),
                ROOT / "critic/emphasis.py",
                ROOT / "critic/emphasis_reading.py",
                ROOT / "critic/simulation.py",
            ]
        },
    )
    save(PUBLIC / "comparison.json", result)
    save(
        PUBLIC / "raw-artifacts.json",
        [
            dict(path=str(p.relative_to(ARCHIVE)), sha256=sha256(p), bytes=p.stat().st_size)
            for p in ARCHIVE.glob("*/*")
        ],
    )
    print("COMPLETE", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    frames, manifest = prepare()
    if not args.analyze:
        runner = SimulationRunner()
        for seed in SEEDS:
            for name, fs in frames.items():
                run(runner, name, seed, fs, manifest)
    analyze(frames, manifest)


if __name__ == "__main__":
    main()

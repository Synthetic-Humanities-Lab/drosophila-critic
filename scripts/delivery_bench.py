"""Run the preregistered local amplitude-delivery bench without altering FlyBrain."""

import argparse
import hashlib
import json
import shutil
import time

import numpy as np

from critic.audio_encoder import encode, write_wav
from critic.config import DT, ROOT
from critic.delivery import bin_rates, equalize, paired_stats, read_wav, variants
from critic.simulation import SimulationRunner, sha256

OUT = ROOT / "results/delivery-v1"
PUBLIC = ROOT / "experiments/delivery-v1"
LABELS = {
    "reference": "Synthetic · matched level",
    "human": "Denny Sayers · matched level",
    "repeat": "Exact repeat",
    "polarity": "Polarity inversion · identical input",
    "pauses": "Redistributed pauses",
    "emphasis": "Alternating emphasis",
    "reordered": "Reversed line order",
}


def save(path, obj):
    path.write_text(json.dumps(obj, allow_nan=False, separators=(",", ":")))


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    waves, lines, sources = {}, {}, {}
    for name, folder in [("reference", "blake-the-fly"), ("human", "blake-sayers")]:
        source = ROOT / "examples" / folder
        x, rate = read_wav(source / "audio.wav")
        if rate != 24000:
            raise ValueError("Unexpected source rate")
        d = json.loads((source / "result.json").read_text())
        waves[name] = x
        lines[name] = d["display"]["lines"]
        sources[name] = dict(
            path=str(source.relative_to(ROOT)),
            sha256=sha256(source / "audio.wav"),
            audio=d["audio"],
        )
        target = PUBLIC / "sources"
        target.mkdir(exist_ok=True)
        shutil.copy2(source / "audio.wav", target / f"{name}.wav")
    for name, (x, times) in variants(waves["reference"], rate, lines["reference"]).items():
        waves[name] = x
        lines[name] = times
    waves, normalization = equalize(waves)
    for name in ["repeat", "polarity"]:
        waves[name] = waves["reference"].copy() * (-1 if name == "polarity" else 1)
        lines[name] = lines["reference"]
        normalization[name] = {**normalization["reference"], "pcm_relation": name}
    manifest = dict(
        version="delivery-v1",
        sample_rate=rate,
        sources=sources,
        conditions={},
        protocol_sha256=sha256(PUBLIC / "PROTOCOL.md"),
        poem=d["display"]["poem"],
    )
    for name in LABELS:
        target = PUBLIC / name
        target.mkdir(exist_ok=True)
        digest = write_wav(target / "audio.wav", waves[name], rate)
        normalization[name]["pcm_sha256"] = hashlib.sha256(
            np.rint(waves[name] * 32768).astype("<i2").tobytes()
        ).hexdigest()
        frames = encode(waves[name], rate)
        width = round(rate * DT)
        save(
            target / "waveform.json",
            [
                [float(part.min()), float(part.max())]
                for start in range(0, len(waves[name]), width)
                if len(part := waves[name][start : start + width])
            ],
        )
        save(target / "encoding.json", frames)
        v = np.array([f["injected_voltage"] for f in frames])
        r = np.array([f["rms"] for f in frames])
        manifest["conditions"][name] = dict(
            label=LABELS[name],
            duration=len(waves[name]) / rate,
            frames=len(frames),
            audio_sha256=digest,
            encoding_sha256=sha256(target / "encoding.json"),
            normalization=normalization[name],
            lines=lines[name],
            mean_frame_rms=float(r.mean()),
            mean_injection=float(v.mean()),
            integrated_injection=float(v.sum() * DT),
            capped_frames=int(np.sum(v >= 0.8)),
        )
    save(PUBLIC / "manifest.json", manifest)
    return manifest


def run_one(runner, name, seed, frames):
    folder = OUT / f"{name}-{seed}"
    folder.mkdir(exist_ok=True)
    marker = folder / "run.json"
    key = dict(
        seed=seed,
        input_sha256=hashlib.sha256(json.dumps(frames, sort_keys=True).encode()).hexdigest(),
    )
    if marker.exists():
        old = json.loads(marker.read_text())
        if (
            old["fly"]["source_sha256"] != runner.source_hashes
            or old["fly"]["data_sha256"] != runner.data_hashes
            or old["fly"]["timestep"] != DT
        ):
            raise ValueError("Cached simulator differs from current source, data or clock")
        if old["key"] != key:
            raise ValueError("Cached run has different inputs")
        return old
    begin = time.perf_counter()
    record = runner.run(frames, folder, seed=seed)
    meta = dict(
        key=key,
        seconds=time.perf_counter() - begin,
        fly=record["fly"],
        spikes_sha256=sha256(folder / "spikes.npz"),
        populations_sha256=sha256(folder / "populations.npz"),
    )
    save(marker, meta)
    print(json.dumps(dict(run=folder.name, seconds=round(meta["seconds"], 2))), flush=True)
    return meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    manifest = prepare()
    if args.analyze:
        analyze(manifest)
        return
    runner = SimulationRunner()
    frames = {name: json.loads((PUBLIC / name / "encoding.json").read_text()) for name in LABELS}

    def run_set(seeds, names):
        for seed in seeds:
            for name in names:
                fs = frames[name]
                zero = [{**f, "rms": 0.0, "injected_voltage": 0.0} for f in fs]
                run_one(runner, f"silence-{len(fs)}", seed, zero)
                run_one(runner, name, seed, fs)

    run_set([64, 65], ["reference", "human"])
    pilot = []
    for seed in [64, 65]:
        for name in ["reference", "human"]:
            pilot.append(json.loads((OUT / f"{name}-{seed}" / "run.json").read_text())["seconds"])
    estimated = sum(pilot) / len(pilot) * 9 * 8
    n = 8 if estimated < 2700 else 6
    selection = dict(
        pilot_seeds=[64, 65],
        run_seconds=pilot,
        projected_eight_seed_seconds=estimated,
        seeds=list(range(64, 64 + n)),
        rule="8 if projected bench <45 min, otherwise 6; exploratory, no significance stopping",
    )
    # Pilot variability is reported without using effect signs to choose replication.
    selection["pilot_downstream"] = []
    for seed in [64, 65]:
        for name in ["reference", "human"]:
            with (
                np.load(OUT / f"{name}-{seed}" / "populations.npz") as p,
                np.load(OUT / f"silence-{len(frames[name])}-{seed}" / "populations.npz") as c,
            ):
                j = list(p["group_names"]).index("direct JON postsynaptic partners")
                for key in ["type_names", "type_sizes", "group_names", "phase"]:
                    if not np.array_equal(p[key], c[key]):
                        raise ValueError(f"Control population mismatch: {key}")
                mask = p["phase"] == "audio"
                selection["pilot_downstream"].append(
                    dict(
                        seed=seed,
                        condition=name,
                        delta=float(
                            (
                                p["group_counts"][mask, j].astype(float)
                                - c["group_counts"][mask, j]
                            ).mean()
                            / (1017 * DT)
                        ),
                    )
                )
    save(PUBLIC / "pilot.json", selection)
    print(json.dumps(selection), flush=True)
    if args.pilot:
        return
    run_set(selection["seeds"], list(LABELS))
    analyze(manifest)


def analyze(manifest):
    seeds = json.loads((PUBLIC / "pilot.json").read_text())["seeds"]
    inventory = json.loads((ROOT / "docs/population-inventory.json").read_text())
    metrics = {}
    traces = {}
    type_effects = {}
    run_meta = {}
    exact = []
    ensembles = {}
    evidence = {}
    names = ["global", "JO-A/B input", "direct JON postsynaptic partners", "descending_neuron"]
    for name, condition in manifest["conditions"].items():
        encoded = json.loads((PUBLIC / name / "encoding.json").read_text())
        input_hash = hashlib.sha256(json.dumps(encoded, sort_keys=True).encode()).hexdigest()
        per_seed = []
        all_traces = []
        types = []
        run_meta[name] = []
        for seed in seeds:
            folder = OUT / f"{name}-{seed}"
            control = OUT / f"silence-{condition['frames']}-{seed}"
            meta = json.loads((folder / "run.json").read_text())
            control_meta = json.loads((control / "run.json").read_text())
            for key in ["configuration", "runtime_weights_sha256", "seed", "data_sha256"]:
                if meta["fly"][key] != control_meta["fly"][key]:
                    raise ValueError(f"Control mismatch: {key}")
            if meta["key"]["input_sha256"] != input_hash:
                raise ValueError("Analysis inputs differ from the actual simulated inputs")
            if meta["fly"]["data_sha256"] != inventory["data_sha256"]:
                raise ValueError("Population inventory differs from simulated data")
            if sha256(folder / "populations.npz") != meta["populations_sha256"]:
                raise ValueError("Recorded counts changed")
            if sha256(control / "populations.npz") != control_meta["populations_sha256"]:
                raise ValueError("Control counts changed")
            run_meta[name].append(meta)
            with (
                np.load(folder / "populations.npz") as p,
                np.load(control / "populations.npz") as c,
            ):
                for key in ["type_names", "type_sizes", "group_names", "phase"]:
                    if not np.array_equal(p[key], c[key]):
                        raise ValueError(f"Control population mismatch: {key}")
                for key in ["global_counts", "group_counts", "phase_counts", "type_sizes"]:
                    evidence[f"{name}_{seed}_{key}"] = p[key]
                    evidence[f"silence_{condition['frames']}_{seed}_{key}"] = c[key]
                mask = p["phase"] == "audio"
                tail = p["phase"] == "tail"
                pre = np.isin(p["phase"], ["warmup", "baseline"])
                assert np.array_equal(p["global_counts"][pre], c["global_counts"][pre])
                idx = [list(p["group_names"]).index(n) for n in names[1:]]
                sizes = np.array(
                    [meta["fly"]["neurons"], *[inventory["groups"][n]["count"] for n in names[1:]]]
                )
                a = np.column_stack([p["global_counts"], p["group_counts"][:, idx]]).astype(float)
                b = np.column_stack([c["global_counts"], c["group_counts"][:, idx]]).astype(float)
                delta = (a - b) / (sizes * DT)
                binned = bin_rates(a - b, sizes)
                # 75 initial steps = 15 bins; audio window then tail, no warmup in plot.
                before = int(np.sum(pre))
                first = before // 5
                t = np.arange(len(binned) - first) * 0.1
                per_seed.append(
                    dict(
                        mean=delta[mask].mean(axis=0).tolist(),
                        tail=delta[tail].mean(axis=0).tolist(),
                        trajectory_rms=np.sqrt(
                            np.mean(bin_rates((a - b)[mask], sizes) ** 2, axis=0)
                        ).tolist(),
                    )
                )
                all_traces.append(binned[first:])
                types.append(
                    (p["phase_counts"][1].astype(float) - c["phase_counts"][1])
                    / (p["type_sizes"] * DT * mask.sum())
                )
                type_names = p["type_names"].copy()
                type_sizes = p["type_sizes"].copy()
            if name in ["repeat", "polarity"]:
                with (
                    np.load(folder / "spikes.npz") as a,
                    np.load(OUT / f"reference-{seed}" / "spikes.npz") as b,
                ):
                    same = all(np.array_equal(a[k], b[k]) for k in a.files)
                    exact.append(dict(condition=name, seed=seed, spikes_identical=same))
                    if not same:
                        raise ValueError("Exact-input control failed")
        metrics[name] = per_seed
        type_effects[name] = np.array(types)
        arr = np.array(all_traces)
        ensembles[name] = arr
        traces[name] = dict(
            time=t.tolist(),
            mean=arr.mean(axis=0).tolist(),
            low=arr.min(axis=0).tolist(),
            high=arr.max(axis=0).tolist(),
        )
    contrasts = {}
    for name in LABELS:
        if name == "reference":
            continue
        entries = {}
        for j, pop in enumerate(names):
            entries[pop] = {
                field: paired_stats(
                    [
                        metrics[name][i][field][j] - metrics["reference"][i][field][j]
                        for i in range(len(seeds))
                    ]
                )
                for field in ["mean", "tail", "trajectory_rms"]
            }
        diff = type_effects[name] - type_effects["reference"]
        eligible = [
            i
            for i, (n, size) in enumerate(zip(type_names, type_sizes))
            if size >= 10 and str(n).strip() and not str(n).startswith(("JO-A", "JO-B"))
        ]
        ranked = sorted(eligible, key=lambda i: -abs(diff[:, i].mean()))[:12]
        common = int(
            min(
                manifest["conditions"][name]["duration"],
                manifest["conditions"]["reference"]["duration"],
            )
            / 0.1
        )
        paired = ensembles[name][:, :common] - ensembles["reference"][:, :common]
        contrasts[name] = dict(
            paired_trace=dict(
                time=(np.arange(common) * 0.1).tolist(),
                mean=paired.mean(axis=0).tolist(),
                low=paired.min(axis=0).tolist(),
                high=paired.max(axis=0).tolist(),
            ),
            temporal_pattern={
                pop: dict(
                    mean_trace_rms=float(np.sqrt(np.mean(paired[:, :, j].mean(axis=0) ** 2))),
                    seed_sd_rms=float(np.sqrt(np.mean(paired[:, :, j].std(axis=0, ddof=1) ** 2))),
                )
                for j, pop in enumerate(names)
            },
            temporal_separation={
                pop: paired_stats(np.sqrt(np.mean(paired[:, :, j] ** 2, axis=1)))
                for j, pop in enumerate(names)
            },
            populations=entries,
            recruitment=[
                dict(
                    name=str(type_names[i]), neurons=int(type_sizes[i]), **paired_stats(diff[:, i])
                )
                for i in ranked
            ],
        )
    result = dict(
        version="delivery-v1",
        seeds=seeds,
        populations=names,
        manifest=manifest,
        metrics=metrics,
        traces=traces,
        contrasts=contrasts,
        exact_controls=exact,
        run_provenance=run_meta,
        population_sizes={
            "global": inventory["neurons"],
            **{n: inventory["groups"][n]["count"] for n in names[1:]},
        },
        band="Observed min–max across seeds, not a confidence interval",
        units="Hz per neuron; all trajectories stimulus minus matched silence",
        interpretation="Descriptive acoustic-model comparison. No poem text enters the simulation or response analysis.",
    )
    result["analysis_source_sha256"] = {
        str(p.relative_to(ROOT)): sha256(p)
        for p in [
            ROOT / "critic/delivery.py",
            ROOT / "critic/simulation.py",
            ROOT / "scripts/delivery_bench.py",
        ]
    }
    evidence["type_names"] = type_names
    with np.load(OUT / f"reference-{seeds[0]}" / "populations.npz") as reference_counts:
        evidence["group_names"] = reference_counts["group_names"]
    np.savez_compressed(PUBLIC / "counts.npz", **evidence)
    result["counts_sha256"] = sha256(PUBLIC / "counts.npz")
    save(PUBLIC / "comparison.json", result)
    save(
        PUBLIC / "raw-artifacts.json",
        dict(
            local_root="results/delivery-v1",
            files=[
                dict(path=str(p.relative_to(OUT)), sha256=sha256(p), bytes=p.stat().st_size)
                for p in sorted(OUT.glob("*/*"))
                if p.suffix in [".npz", ".json"]
            ],
        ),
    )
    print("ANALYSIS COMPLETE", flush=True)


if __name__ == "__main__":
    main()

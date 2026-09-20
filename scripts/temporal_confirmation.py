"""Held-out temporal confirmation using the original SimulationRunner."""

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from critic.audio_encoder import encode, write_wav
from critic.config import DT, ROOT
from critic.delivery import bin_rates, read_wav
from critic.simulation import SimulationRunner, sha256
from critic.temporal import episodes, paired_summary, temporal_evidence
from critic.temporal_reading import AffectInput, Episode, interpret

PUBLIC = ROOT / "experiments/temporal-v2"
ARCHIVE = ROOT / "results/temporal-v2"
V1 = ROOT / "experiments/delivery-v1"
SEEDS = list(range(101, 109))
TAIL = 5.0
GROUPS = [
    "JO-A/B input",
    "direct JON postsynaptic partners",
    "descending_neuron",
    "DNa02",
    "DNp01",
    "MDN",
    "pIP10",
]


def save(path, data):
    path.write_text(json.dumps(data, allow_nan=False, separators=(",", ":")))


def prepare():
    old = json.loads((V1 / "manifest.json").read_text())
    frames = {}
    conditions = {}
    for name in ["reference", "human", "pauses", "reordered"]:
        frames[name] = json.loads((V1 / name / "encoding.json").read_text())
        conditions[name] = old["conditions"][name]
    x, rate = read_wav(V1 / "reference/audio.wav")
    lines = conditions["reference"]["lines"]
    starts = [round(line["start"] * rate) for line in lines]
    ends = [round(line["end"] * rate) for line in lines]
    stops = starts[1:] + [len(x)]
    lengths = [stop - end for stop, end in zip(stops, ends)]
    donor = next(i for i, line in enumerate(lines) if line["line"] == 8)
    recipient = next(i for i, line in enumerate(lines) if line["line"] == 4)
    move = round(0.18 * rate)
    if lengths[donor] < move or any(np.any(x[e:s]) for e, s in zip(ends, stops)):
        raise ValueError("Expected verified digital silence")
    lengths[donor] -= move
    lengths[recipient] += move
    parts = []
    newlines = []
    pos = 0
    for line, start, end, gap in zip(lines, starts, ends, lengths):
        speech = x[start:end]
        parts.extend([speech, np.zeros(gap)])
        newlines.append(dict(line=line["line"], start=pos / rate, end=(pos + len(speech)) / rate))
        pos += len(speech) + gap
    y = np.concatenate(parts)
    if not np.array_equal(np.sort(x), np.sort(y)):
        raise ValueError("Pause edit changed source samples")
    write_wav(PUBLIC / "localized-pause.wav", y, rate)
    frames["localized"] = encode(y, rate)
    conditions["localized"] = dict(
        label="One relocated pause", duration=len(y) / rate, lines=newlines
    )
    fs = frames["reference"]
    frames["frame_reverse"] = [
        {**f, "injected_voltage": fs[-1 - i]["injected_voltage"], "rms": fs[-1 - i]["rms"]}
        for i, f in enumerate(fs)
    ]
    conditions["frame_reverse"] = dict(
        label="Reversed injected frames — no oral performance", duration=len(fs) * DT, lines=[]
    )
    for name, fs in frames.items():
        save(PUBLIC / f"{name}-encoding.json", fs)
        conditions[name] = {
            **conditions[name],
            "input_hash": hashlib.sha256(json.dumps(fs, sort_keys=True).encode()).hexdigest(),
            "integrated_drive": sum(f["injected_voltage"] for f in fs) * DT,
        }
    if sorted(f["injected_voltage"] for f in frames["reference"]) != sorted(
        f["injected_voltage"] for f in frames["frame_reverse"]
    ):
        raise ValueError("Input multiset changed")
    manifest = dict(
        seeds=SEEDS,
        tail_seconds=TAIL,
        conditions=conditions,
        protocol_sha256=sha256(PUBLIC / "PROTOCOL.md"),
    )
    save(PUBLIC / "manifest.json", manifest)
    return frames, manifest


def run(runner, name, seed, frames):
    directory = ARCHIVE / f"{name}-{seed}"
    directory.mkdir(parents=True, exist_ok=True)
    key = dict(
        seed=seed,
        tail=TAIL,
        input=hashlib.sha256(json.dumps(frames, sort_keys=True).encode()).hexdigest(),
        adapter=sha256(ROOT / "critic/simulation.py"),
    )
    if (directory / "run.json").exists():
        if json.loads((directory / "run.json").read_text())["key"] != key:
            raise ValueError("Cached run mismatch")
        return
    begin = time.perf_counter()
    record = runner.run(frames, directory, seed=seed, tail_seconds=TAIL)
    save(
        directory / "run.json",
        dict(
            key=key,
            seconds=time.perf_counter() - begin,
            fly=record["fly"],
            counts_sha256=sha256(directory / "populations.npz"),
            spikes_sha256=sha256(directory / "spikes.npz"),
        ),
    )
    print(name, seed, round(time.perf_counter() - begin, 2), flush=True)


def analyze(frames, manifest):
    inventory = json.loads((ROOT / "docs/population-inventory.json").read_text())
    sizes = np.array([inventory["groups"][g]["count"] for g in GROUPS])
    ensemble = {}
    metrics = {}
    events = {}
    evidence = {}
    provenance = {}
    for name, fs in frames.items():
        trajectories = []
        rates = []
        tails = []
        tailbins = []
        onsets = []
        provenance[name] = []
        for seed in SEEDS:
            directory = ARCHIVE / f"{name}-{seed}"
            control = ARCHIVE / f"silence-{len(fs)}-{seed}"
            meta = json.loads((directory / "run.json").read_text())
            cm = json.loads((control / "run.json").read_text())
            if meta["key"]["input"] != manifest["conditions"][name]["input_hash"]:
                raise ValueError("Changed inputs")
            for key in ["configuration", "seed", "runtime_weights_sha256", "data_sha256"]:
                if meta["fly"][key] != cm["fly"][key]:
                    raise ValueError("Control mismatch")
            if meta["fly"]["data_sha256"] != inventory["data_sha256"]:
                raise ValueError("Inventory mismatch")
            provenance[name].append(meta)
            with (
                np.load(directory / "populations.npz") as p,
                np.load(control / "populations.npz") as c,
            ):
                if (
                    sha256(directory / "populations.npz") != meta["counts_sha256"]
                    or sha256(control / "populations.npz") != cm["counts_sha256"]
                ):
                    raise ValueError("Counts changed")
                idx = [list(p["group_names"]).index(g) for g in GROUPS]
                audio = p["phase"] == "audio"
                tail = p["phase"] == "tail"
                pre = np.isin(p["phase"], ["baseline", "warmup"])
                if not np.array_equal(p["group_counts"][pre], c["group_counts"][pre]):
                    raise ValueError("Initial trajectories differ")
                raw = p["group_counts"].astype(float) - c["group_counts"]
                delta = raw[:, idx] / (sizes * DT)
                a = delta[audio]
                t = delta[tail]
                trajectories.append(bin_rates(raw[audio][:, idx], sizes))
                rates.append(a.mean(axis=0))
                tails.append(t.mean(axis=0))
                tailbins.append(t.reshape(5, 50, len(GROUPS)).mean(axis=1))
                event_rows = {}
                for line in manifest["conditions"][name]["lines"]:
                    step = round(line["start"] / DT)
                    width = round(0.3 / DT)
                    if line["end"] > line["start"] and step >= width and step + width <= len(a):
                        event_rows[str(line["line"])] = (
                            a[step : step + width].mean(axis=0)
                            - a[step - width : step].mean(axis=0)
                        ).tolist()
                onsets.append(event_rows)
                for kind, z in [(name, p), (f"silence_{len(fs)}", c)]:
                    for k in ["group_counts", "global_counts", "phase_counts", "type_sizes"]:
                        evidence[f"{kind}_{seed}_{k}"] = z[k]
                evidence["type_names"] = p["type_names"]
                evidence["group_names"] = p["group_names"]
        ensemble[name] = np.array(trajectories)
        metrics[name] = dict(
            mean=np.array(rates).tolist(),
            tail=np.array(tails).tolist(),
            tail_seconds=np.array(tailbins).tolist(),
        )
        events[name] = onsets
    comparisons = {}
    for name in frames:
        if name == "reference":
            continue
        n = int(
            min(
                manifest["conditions"][name]["duration"],
                manifest["conditions"]["reference"]["duration"],
            )
            / 0.1
        )
        paired = ensemble[name][:, :n] - ensemble["reference"][:, :n]
        populations = {}
        for j, g in enumerate(GROUPS):
            populations[g] = dict(
                temporal=temporal_evidence(paired[:, :, j]),
                mean=paired_summary(
                    np.array(metrics[name]["mean"])[:, j]
                    - np.array(metrics["reference"]["mean"])[:, j]
                ),
                tail=paired_summary(
                    np.array(metrics[name]["tail"])[:, j]
                    - np.array(metrics["reference"]["tail"])[:, j]
                ),
                tail_seconds=[
                    paired_summary(
                        np.array(metrics[name]["tail_seconds"])[:, k, j]
                        - np.array(metrics["reference"]["tail_seconds"])[:, k, j]
                    )
                    for k in range(5)
                ],
            )
        selected = episodes(paired[:, :, 1])
        summary = AffectInput(
            seeds=len(SEEDS),
            temporal_criterion_met=populations[GROUPS[1]]["temporal"]["criterion_met"],
            descending_criterion_met=populations[GROUPS[2]]["temporal"]["criterion_met"],
            mean_rate_difference=populations[GROUPS[1]]["mean"]["mean"],
            tail_mean_difference=populations[GROUPS[1]]["tail"]["mean"],
            episodes=[
                Episode(
                    start=e["start"],
                    end=e["end"],
                    mean=e["mean"],
                    agreeing_seeds=(
                        e["positive"]
                        if e["mean"] > 0
                        else e["negative"]
                        if e["mean"] < 0
                        else len(SEEDS) - e["positive"] - e["negative"]
                    ),
                )
                for e in selected
            ],
        )
        reading = interpret(summary)
        save(PUBLIC / f"{name}-interpretation-input.json", summary.model_dump())
        comparisons[name] = dict(
            populations=populations,
            episodes=selected,
            reading=reading,
            trace=dict(
                time=(np.arange(n) * 0.1).tolist(),
                mean=paired[:, :, 1].mean(axis=0).tolist(),
                low=paired[:, :, 1].min(axis=0).tolist(),
                high=paired[:, :, 1].max(axis=0).tolist(),
            ),
        )
    onset_steps = {
        name: round(
            next(
                line["start"] for line in manifest["conditions"][name]["lines"] if line["line"] == 6
            )
            / DT
        )
        for name in ["reference", "localized"]
    }
    local_inputs = {
        name: [frame["injected_voltage"] for frame in frames[name][step - 15 : step + 15]]
        for name, step in onset_steps.items()
    }
    if local_inputs["reference"] != local_inputs["localized"]:
        raise ValueError("Local onset injection windows differ")
    resumption = {}
    for j, group in enumerate(GROUPS):
        values = [
            events["localized"][i]["6"][j] - events["reference"][i]["6"][j]
            for i in range(len(SEEDS))
        ]
        resumption[group] = paired_summary(values)
    np.savez_compressed(PUBLIC / "counts.npz", **evidence)
    result = dict(
        manifest=manifest,
        groups=GROUPS,
        comparisons=comparisons,
        metrics=metrics,
        onset_changes=events,
        localized_resumption=dict(
            line=6,
            window_seconds=0.3,
            input_windows_identical=True,
            onset_steps=onset_steps,
            populations=resumption,
        ),
        provenance=provenance,
        counts_sha256=sha256(PUBLIC / "counts.npz"),
        source_sha256={
            str(p.relative_to(ROOT)): sha256(p)
            for p in [
                Path(__file__),
                ROOT / "critic/temporal.py",
                ROOT / "critic/temporal_reading.py",
                ROOT / "critic/simulation.py",
            ]
        },
    )
    save(PUBLIC / "confirmation.json", result)
    save(
        PUBLIC / "raw-artifacts.json",
        [
            dict(path=str(p.relative_to(ARCHIVE)), bytes=p.stat().st_size, sha256=sha256(p))
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
                zero = [{**f, "injected_voltage": 0.0, "rms": 0.0} for f in fs]
                run(runner, f"silence-{len(fs)}", seed, zero)
                run(runner, name, seed, fs)
    analyze(frames, manifest)


if __name__ == "__main__":
    main()

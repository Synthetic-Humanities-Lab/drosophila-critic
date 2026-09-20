"""Run the declared matched-history experiment on the unchanged FlyBrain adapter."""

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from critic.audio_encoder import encode, write_wav
from critic.config import BASELINE_SECONDS, DT, ROOT, WARMUP_SECONDS
from critic.delivery import bin_rates, read_wav
from critic.history import CONTRASTS, GAPS, factorial, stimuli, summarize
from critic.history_reading import GapSummary, HistorySummary, interpret
from critic.simulation import SimulationRunner, sha256

PUBLIC = ROOT / "experiments/history-v3"
ARCHIVE = ROOT / "results/history-v3"
SEEDS = list(range(201, 209))
GROUPS = [
    "JO-A/B input",
    "direct JON postsynaptic partners",
    "descending_neuron",
    "DNa02",
    "DNp01",
    "MDN",
    "pIP10",
]
BEFORE = round((WARMUP_SECONDS + BASELINE_SECONDS) / DT)


def save(path, data):
    path.write_text(json.dumps(data, allow_nan=False, separators=(",", ":")))


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def prepare():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    source = ROOT / "experiments/delivery-v1/reference/audio.wav"
    x, rate = read_wav(source)
    frames, conditions = {}, {}
    for name, (audio, meta) in stimuli(x, rate).items():
        folder = PUBLIC / name
        folder.mkdir(exist_ok=True)
        audio_hash = write_wav(folder / "audio.wav", audio, rate)
        decoded, decoded_rate = read_wav(folder / "audio.wav")
        if decoded_rate != rate or not np.array_equal(decoded, audio):
            raise ValueError("Exported PCM differs from stimulus")
        fs = encode(decoded, rate)
        frames[name] = fs
        save(folder / "encoding.json", fs)
        conditions[name] = dict(
            **meta,
            frames=len(fs),
            input_sha256=digest(fs),
            audio_sha256=audio_hash,
            integrated_drive=sum(f["injected_voltage"] for f in fs) * DT,
        )
    for gap in GAPS:
        prefix = f"g{round(gap * 1000)}"
        ap, bp = [frames[f"{prefix}_{h}_probe"] for h in ("a", "b")]
        start = round((6 + gap) / DT)

        def drive(fs):
            return [f["injected_voltage"] for f in fs]

        if sorted(drive(ap[:300])) != sorted(drive(bp[:300])) or drive(ap[start:]) != drive(
            bp[start:]
        ):
            raise ValueError("History dose or common probe differs")
        for history in ("a", "b"):
            p, q = [frames[f"{prefix}_{history}_{ending}"] for ending in ("probe", "quiet")]
            if p[:start] != q[:start] or any(drive(q[start:])):
                raise ValueError("Quiet continuation mismatch")
    manifest = dict(
        seeds=SEEDS,
        gaps=GAPS,
        conditions=conditions,
        source_sha256=sha256(source),
        protocol_sha256=sha256(PUBLIC / "PROTOCOL.md"),
        before_steps=BEFORE,
        tail_seconds=1,
        source="experiments/delivery-v1/reference/audio.wav",
    )
    save(PUBLIC / "manifest.json", manifest)
    return frames, manifest


def run(runner, name, seed, fs, manifest):
    directory = ARCHIVE / f"{name}-{seed}"
    directory.mkdir(parents=True, exist_ok=True)
    key = dict(
        seed=seed,
        input=digest(fs),
        protocol=manifest["protocol_sha256"],
        adapter=sha256(ROOT / "critic/simulation.py"),
        upstream=runner.source_hashes,
        data=runner.data_hashes,
        tail_seconds=1,
    )
    if (directory / "run.json").exists():
        if json.loads((directory / "run.json").read_text())["key"] != key:
            raise ValueError("Cached run does not match experiment")
        return
    begin = time.perf_counter()
    record = runner.run(fs, directory, seed=seed)
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


def equal_spikes(first, second, until=None):
    with np.load(first / "spikes.npz") as a, np.load(second / "spikes.npz") as b:
        stop = len(a["offsets"]) - 1 if until is None else until
        return bool(
            np.array_equal(a["offsets"][: stop + 1], b["offsets"][: stop + 1])
            and np.array_equal(
                a["neuron_indices"][: a["offsets"][stop]], b["neuron_indices"][: b["offsets"][stop]]
            )
        )


def analyze(frames, manifest):
    inventory = json.loads((ROOT / "docs/population-inventory.json").read_text())
    sizes = np.array([inventory["groups"][g]["count"] for g in GROUPS])
    all_counts, evidence, provenance = {}, {}, {}
    controls = []
    reference_config = None
    for name, fs in frames.items():
        all_counts[name], provenance[name] = [], []
        for seed in SEEDS:
            directory = ARCHIVE / f"{name}-{seed}"
            meta = json.loads((directory / "run.json").read_text())
            if (
                meta["key"]["input"] != digest(fs)
                or meta["key"]["protocol"] != manifest["protocol_sha256"]
            ):
                raise ValueError("Input or protocol mismatch")
            if (
                meta["fly"]["data_sha256"] != inventory["data_sha256"]
                or not meta["fly"]["weights_unchanged"]
            ):
                raise ValueError("Connectome mismatch")
            signature = {
                key: meta["fly"][key]
                for key in (
                    "configuration",
                    "runtime_weights_sha256",
                    "source_sha256",
                    "environment",
                )
            }
            if reference_config is None:
                reference_config = signature
            if signature != reference_config or meta["fly"]["seed"] != seed:
                raise ValueError("Simulation configuration changed")
            if (
                sha256(directory / "populations.npz") != meta["counts_sha256"]
                or sha256(directory / "spikes.npz") != meta["spikes_sha256"]
            ):
                raise ValueError("Raw artifacts changed")
            provenance[name].append(meta)
            with np.load(directory / "populations.npz") as p:
                idx = [list(p["group_names"]).index(g) for g in GROUPS]
                start = BEFORE + round(manifest["conditions"][name]["probe_start"] / DT)
                all_counts[name].append(
                    p["group_counts"][start : start + 100, idx].astype(np.int64)
                )
                for key in ("group_counts", "global_counts", "phase_counts", "type_sizes"):
                    evidence[f"{name}_{seed}_{key}"] = p[key]
                evidence["group_names"], evidence["type_names"] = p["group_names"], p["type_names"]
            baseline = ARCHIVE / f"g0_a_probe-{seed}"
            if not equal_spikes(directory, baseline, BEFORE):
                raise ValueError("Baseline differs")
            if name.endswith("probe"):
                quiet = ARCHIVE / f"{name.removesuffix('probe')}quiet-{seed}"
                if not equal_spikes(directory, quiet, start):
                    raise ValueError("Probe and quiet diverged before probe onset")
        all_counts[name] = np.array(all_counts[name])
    for seed in SEEDS:
        original = ARCHIVE / f"g0_a_probe-{seed}"
        duplicate = ARCHIVE / f"repeat-{seed}"
        if not equal_spikes(original, duplicate):
            raise ValueError("Identical input did not reproduce complete spikes")
        controls.append(
            dict(
                seed=seed,
                complete_spikes_identical=True,
                duplicate=json.loads((duplicate / "run.json").read_text()),
            )
        )
    gaps = {}
    for gap in GAPS:
        prefix = f"g{round(gap * 1000)}"
        counts = factorial(
            *(
                all_counts[f"{prefix}_{h}_{e}"]
                for h, e in (("a", "probe"), ("a", "quiet"), ("b", "probe"), ("b", "quiet"))
            )
        )
        populations = {}
        for j, group in enumerate(GROUPS):
            populations[group] = {}
            for contrast in CONTRASTS:
                rates = np.array([bin_rates(c[:, j], sizes[j]) for c in counts[contrast]])
                populations[group][contrast] = summarize(rates)
        gaps[str(gap)] = dict(gap=gap, populations=populations)
    summary = HistorySummary(
        seeds=len(SEEDS),
        gaps=[
            GapSummary(
                gap_seconds=gap["gap"],
                early_interaction=gap["populations"][GROUPS[1]]["interaction"]["early"]["temporal"][
                    "criterion_met"
                ],
                full_interaction=gap["populations"][GROUPS[1]]["interaction"]["full"]["temporal"][
                    "criterion_met"
                ],
                early_lingering=gap["populations"][GROUPS[1]]["lingering"]["early"]["temporal"][
                    "criterion_met"
                ],
                full_lingering=gap["populations"][GROUPS[1]]["lingering"]["full"]["temporal"][
                    "criterion_met"
                ],
                probe_after_a=gap["populations"][GROUPS[1]]["after_a"]["early"]["temporal"][
                    "criterion_met"
                ],
                probe_after_b=gap["populations"][GROUPS[1]]["after_b"]["early"]["temporal"][
                    "criterion_met"
                ],
                full_probe_after_a=gap["populations"][GROUPS[1]]["after_a"]["full"]["temporal"][
                    "criterion_met"
                ],
                full_probe_after_b=gap["populations"][GROUPS[1]]["after_b"]["full"]["temporal"][
                    "criterion_met"
                ],
                descending_interaction=gap["populations"][GROUPS[2]]["interaction"]["early"][
                    "temporal"
                ]["criterion_met"],
                early_mean=gap["populations"][GROUPS[1]]["interaction"]["early"]["mean"]["mean"],
            )
            for gap in gaps.values()
        ],
    )
    save(PUBLIC / "interpretation-input.json", summary.model_dump())
    np.savez_compressed(PUBLIC / "counts.npz", **evidence)
    result = dict(
        manifest=manifest,
        interpretation=interpret(summary),
        groups=GROUPS,
        gaps=gaps,
        controls=controls,
        provenance=provenance,
        counts_sha256=sha256(PUBLIC / "counts.npz"),
        source_sha256={
            str(p.relative_to(ROOT)): sha256(p)
            for p in [
                Path(__file__).resolve(),
                ROOT / "critic/history.py",
                ROOT / "critic/history_reading.py",
                ROOT / "critic/simulation.py",
                ROOT / "critic/temporal.py",
            ]
        },
    )
    save(PUBLIC / "comparison.json", result)
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
                run(runner, name, seed, fs, manifest)
            run(runner, "repeat", seed, frames["g0_a_probe"], manifest)
    analyze(frames, manifest)


if __name__ == "__main__":
    main()

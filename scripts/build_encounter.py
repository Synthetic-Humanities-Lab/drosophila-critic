"""Run the declared mechanical-receiver encounter; export only curated Blake data."""

import hashlib
import json
import shutil
import time

import numpy as np

from critic.config import ROOT
from critic.delivery import equalize
from critic.neural_display import export_neural_display
from critic.performance import (
    GROUPS,
    RATE,
    SEEDS,
    analyze_pair,
    decode_upload,
    measure,
    save_pcm,
)
from critic.performance_passages import passage_report
from critic.performance_reading import ComparisonSummary, interpret_comparison
from critic.pipeline import save_json
from critic.receiver.provisional import encode_provisional
from critic.simulation import SimulationRunner, sha256

PUBLIC = ROOT / "experiments/encounter-v1"
RAW = ROOT / "results/encounter-v1"


def load_record(path, runner, sound_frames):
    with np.load(path / "populations.npz", allow_pickle=False) as archive:
        record = {k: archive[k] for k in archive.files}
    record["group_names"] = record["group_names"].tolist()
    record["group_sizes"] = [len(runner.groups[n]) for n in record["group_names"]]
    record["before"] = int(np.flatnonzero(record["phase"] == "audio")[0])
    # Mechanical ringdown belongs to persistence, not to the spoken performance.
    record["phase"][record["before"] + sound_frames :] = "tail"
    with np.load(path / "spikes.npz") as spikes:
        neurons, offsets = spikes["neuron_indices"], spikes["offsets"]
        counts = np.zeros((3, len(runner.type_names)), dtype=np.uint64)
        for i, phase in enumerate(record["phase"]):
            slot = {"baseline": 0, "audio": 1, "tail": 2}.get(phase)
            if slot is not None:
                fired = neurons[int(offsets[i]) : int(offsets[i + 1])]
                counts[slot] += np.bincount(
                    runner.type_index[fired], minlength=len(runner.type_names)
                ).astype(np.uint64)
    record["phase_type_counts"] = counts
    return record


def summary_for(response, durations):
    return ComparisonSummary(
        durations=durations,
        seeds=list(SEEDS),
        differences=[
            dict(
                population=r["population"],
                mean_rate_difference=r["rate"]["mean"],
                seed_differences=r["rate"]["values"],
                persistence_difference=r["tail"]["mean"],
                temporal_separation_rms=r["temporal_separation_rms"],
                temporal_variability_rms=r["temporal_variability_rms"],
            )
            for r in response["differences"]
        ],
        passages=[
            dict(
                number=p["number"],
                durations=[p["performances"][n]["duration"] for n in ("a", "b")],
                mean_drives=[p["performances"][n]["mean_drive"] for n in ("a", "b")],
                direct_rate_difference=p["populations"][1]["difference"]["mean"],
                seed_differences=p["populations"][1]["difference"]["values"],
                boundary_direction_consistent=p["populations"][1][
                    "same_direction_across_seeds_and_boundaries"
                ],
            )
            for p in response["passage_comparison"]["passages"]
        ],
    )


def main():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    protocol_hash = sha256(ROOT / "docs/ENCOUNTER.md")
    source_hashes = {
        n: sha256(ROOT / n)
        for n in (
            "scripts/build_encounter.py",
            "critic/receiver/provisional.py",
            "critic/receiver/healthy.py",
            "critic/simulation.py",
            "critic/performance.py",
            "critic/performance_passages.py",
        )
    }
    original = json.loads((ROOT / "experiments/performance-v1/result.json").read_text())
    passages = [
        {n: {k: p["performances"][n][k] for k in ("start", "end")} for n in ("a", "b")}
        for p in original["response"]["passage_comparison"]["passages"]
    ]
    waves, metadata = {}, {}
    for n, source in (("a", "reference"), ("b", "human")):
        path = ROOT / f"experiments/delivery-v1/sources/{source}.wav"
        waves[n], metadata[n] = decode_upload(path.read_bytes())
        if metadata[n]["sha256"] != original["audio"][n]["sha256"]:
            raise ValueError("Stanza annotations do not match the original audio")
    waves, levels = equalize(waves)
    for n in waves:
        metadata[n]["normalization"] = levels[n]
        metadata[n]["processed_sha256"] = save_pcm(PUBLIC / f"{n}.wav", waves[n])
    runner = SimulationRunner()
    all_results, all_frames, runs = {}, {}, []
    started = time.monotonic()
    for strength in (0.5, 1.0, 2.0):
        measured = {"a": [], "b": []}
        frames, encoders = {}, {}
        for n in waves:
            frames[n], encoders[n] = encode_provisional(waves[n], RATE, "displacement", strength)
        for seed in SEEDS:
            for n in waves:
                pair = []
                for condition in ("sound", "silence"):
                    key = f"{n}-{condition}-{seed}" + (
                        f"-g{strength:g}" if condition == "sound" else ""
                    )
                    path = RAW / key
                    path.mkdir(exist_ok=True)
                    stimulus = (
                        frames[n]
                        if condition == "sound"
                        else [{"injected_voltage": 0.0}] * len(frames[n])
                    )
                    identity = hashlib.sha256(
                        json.dumps(
                            [protocol_hash, source_hashes, stimulus, seed], sort_keys=True
                        ).encode()
                    ).hexdigest()
                    done = path / "complete.json"
                    if done.exists():
                        if json.loads(done.read_text())["identity"] != identity:
                            raise ValueError(f"Stale run cache: {key}; use a new raw directory")
                    else:
                        print(f"RUN {key}", flush=True)
                        record = runner.run(stimulus, path, seed=seed, tail_seconds=3)
                        save_json(path / "provenance.json", record["fly"])
                        save_json(done, {"identity": identity})
                    pair.append(load_record(path, runner, encoders[n]["sound_frames"]))
                    if strength == 1:
                        runs.append(
                            {
                                "id": key,
                                "fly": json.loads((path / "provenance.json").read_text()),
                                "counts_sha256": sha256(path / "populations.npz"),
                                "spikes_sha256": sha256(path / "spikes.npz"),
                            }
                        )
                        if condition == "sound" and seed == SEEDS[0]:
                            spatial = export_neural_display(runner, path)
                            spatial["seed"] = seed
                            save_json(PUBLIC / f"spatial-{n}.json", spatial)
                measured[n].append(measure(*pair))
        durations = [metadata[n]["duration"] for n in ("a", "b")]
        response = analyze_pair(measured, durations, runner.type_names)
        response["passage_comparison"] = passage_report(
            measured, frames, passages, dict(zip(("a", "b"), durations)), GROUPS
        )
        all_results[strength] = response
        all_frames[strength] = {"frames": frames, "metadata": encoders}
        save_json(PUBLIC / f"response-g{strength:g}.json", response)
    response = all_results[1.0]
    summary = summary_for(response, durations)
    result = dict(
        schema_version="encounter-v1",
        poem_id=original["poem_id"],
        audio=metadata,
        encoder=all_frames[1.0]["metadata"],
        seeds=list(SEEDS),
        runs=runs,
        implementation_sha256=source_hashes,
        protocol_sha256=protocol_hash,
        response=response,
        reading={
            "provider": "response-only-template-v2",
            "input_summary": summary.model_dump(),
            "text": interpret_comparison(summary),
        },
        wall_seconds=time.monotonic() - started,
    )
    save_json(PUBLIC / "result.json", result)
    save_json(PUBLIC / "reading-input.json", summary.model_dump())
    save_json(PUBLIC / "encoding.json", all_frames[1.0])
    sensitivity = {
        "strengths": [0.5, 1, 2],
        "nominal_selected_before_runs": 1,
        "direct_difference_by_strength": {
            str(k): v["differences"][1]["rate"] for k, v in all_results.items()
        },
        "passage_consistency": [
            all(
                v["passage_comparison"]["passages"][i]["populations"][1][
                    "same_direction_across_seeds_and_boundaries"
                ]
                for v in all_results.values()
            )
            and len(
                {
                    np.sign(
                        v["passage_comparison"]["passages"][i]["populations"][1]["difference"][
                            "mean"
                        ]
                    )
                    for v in all_results.values()
                }
            )
            == 1
            for i in range(5)
        ],
    }
    save_json(PUBLIC / "sensitivity.json", sensitivity)
    values = np.concatenate(
        [np.asarray(p["timeline"]["mean"])[:, 1] for p in response["performances"].values()]
    )
    manifest = dict(
        schema_version="encounter-manifest-v1",
        title="The Drosophila Critic",
        poem=json.loads((ROOT / "examples/example.json").read_text())["poem"],
        result="result.json",
        encoding="encoding.json",
        sensitivity="sensitivity.json",
        receiver="Published antennal filter · provisional neural coupling",
        spatial_seed=SEEDS[0],
        scales={
            "downstream_min": float(min(0, values.min())),
            "downstream_max": float(max(0.1, values.max())),
            "input_max": 0.8,
        },
        performances={
            n: {
                "label": label,
                "credit": credit,
                "audio": f"{n}.wav",
                "spatial": f"spatial-{n}.json",
                "duration": metadata[n]["duration"],
                "passages": [p[n] for p in passages],
            }
            for n, label, credit in (
                ("a", "Robot", "Kokoro af_sarah · fixed synthetic voice"),
                ("b", "Human", "Denny Sayers · LibriVox, 2006"),
            )
        },
    )
    save_json(PUBLIC / "manifest.json", manifest)
    shutil.copy2(ROOT / "docs/ENCOUNTER.md", PUBLIC / "METHOD.md")
    print(json.dumps(sensitivity, indent=2), flush=True)


if __name__ == "__main__":
    main()

"""Reanalyze stored counts with prior Blake stanza timings; no new fly runs."""

import hashlib
import json
from pathlib import Path

import numpy as np

from critic.performance import GROUPS, measure
from critic.performance_passages import passage_report
from critic.performance_reading import ComparisonSummary, interpret_comparison
from critic.pipeline import save_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/performance-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    whole = OUT / "whole-result.json"
    if not whole.exists():
        whole.write_bytes((OUT / "result.json").read_bytes())
    result = json.loads(whole.read_text())
    directory = ROOT / "results" / result["id"]
    source = ROOT / "experiments/passages-v5/comparison.json"
    earlier = json.loads(source.read_text())
    durations = {name: result["audio"][name]["duration"] for name in ("a", "b")}
    passages = []
    for passage in earlier["passages"]:
        pair = {}
        for name, old in (("a", "reference"), ("b", "human")):
            window = passage["performances"][old]
            pair[name] = {"start": window["start"], "end": window["end"]}
        passages.append(pair)
    inventory_path = ROOT / "docs/population-inventory.json"
    inventory = json.loads(inventory_path.read_text())
    evidence = {str(p.relative_to(ROOT)): sha(p) for p in (whole, source, inventory_path)}
    frames = json.loads((OUT / "encoding.json").read_text())["frames"]
    evidence["experiments/performance-v1/encoding.json"] = sha(OUT / "encoding.json")
    measurements = {"a": [], "b": []}
    for name, old in (("a", "reference"), ("b", "human")):
        source_audio = ROOT / f"experiments/delivery-v1/sources/{old}.wav"
        if sha(source_audio) != result["audio"][name]["sha256"]:
            raise ValueError("Timing annotations no longer refer to the same source recording")
        evidence[str(source_audio.relative_to(ROOT))] = sha(source_audio)
        for seed in result["seeds"]:
            records = []
            for condition in ("sound", "silence"):
                path = directory / f"{name}-{condition}-{seed}" / "populations.npz"
                evidence[str(path.relative_to(ROOT))] = sha(path)
                with np.load(path, allow_pickle=False) as archive:
                    record = {key: archive[key] for key in archive.files}
                record["group_names"] = record["group_names"].tolist()
                record["group_sizes"] = [
                    inventory["groups"][str(g)]["count"] for g in record["group_names"]
                ]
                record["before"] = int(np.flatnonzero(record["phase"] == "audio")[0])
                record["phase_type_counts"] = record["phase_counts"]
                records.append(record)
            measurements[name].append(measure(*records))
    for name in ("a", "b"):
        for j in range(len(GROUPS)):
            expected = result["response"]["performances"][name]["populations"][j]["rate"]["values"]
            observed = [m["rate"][j] for m in measurements[name]]
            if not np.array_equal(expected, observed):
                raise ValueError(
                    "Archived counts do not reproduce the published whole-recording means"
                )
    report = passage_report(measurements, frames, passages, durations, GROUPS)
    result["response"]["passage_comparison"] = report
    summary = dict(result["reading"]["input_summary"])
    summary["passages"] = [
        {
            "number": row["number"],
            "durations": [row["performances"][n]["duration"] for n in ("a", "b")],
            "mean_drives": [row["performances"][n]["mean_drive"] for n in ("a", "b")],
            "direct_rate_difference": row["populations"][1]["difference"]["mean"],
            "seed_differences": row["populations"][1]["difference"]["values"],
            "boundary_direction_consistent": row["populations"][1][
                "same_direction_across_seeds_and_boundaries"
            ],
        }
        for row in report["passages"]
    ]
    summary = ComparisonSummary.model_validate(summary)
    result["reading"] = {
        "provider": "response-only-template-v2",
        "input_summary": summary.model_dump(),
        "text": interpret_comparison(summary),
    }
    result["passage_analysis"] = {
        "annotation_source": "Existing Blake stanza timings; human boundaries approximate, synthetic boundaries from the rendering. These were defined before these four-seed runs.",
        "source_sha256": evidence,
        "analysis_sha256": {
            name: sha(ROOT / name)
            for name in (
                "scripts/annotate_performance_example.py",
                "critic/performance.py",
                "critic/performance_passages.py",
                "critic/performance_reading.py",
            )
        },
    }
    save_json(OUT / "reading-input.json", summary.model_dump())
    save_json(OUT / "result.json", result)
    print(json.dumps(summary.model_dump()["passages"], indent=2))


if __name__ == "__main__":
    main()

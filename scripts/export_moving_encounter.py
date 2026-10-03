"""Publish a new body-playback edition without replacing historical neural data."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def aggregate(values):
    return {
        "mean": sum(values) / len(values),
        "minimum": min(values),
        "maximum": max(values),
        "n": len(values),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Local scene inspection only; reports unmet gates explicitly",
    )
    args = parser.parse_args()
    root = Path("results/body-controller/trajectories")
    out = Path("experiments/encounter-v3")
    out.mkdir(exist_ok=True)
    m = json.loads(Path("experiments/encounter-v2/manifest.json").read_text())
    m["schema_version"] = "encounter-manifest-v3"
    m["body"] = {
        "version": "listening-body-v1",
        "seed": 1101,
        "qualified": not args.preview,
        "description": "Frozen connectome → declared neural adapter → frozen body policies → MuJoCo trajectory",
    }
    report = {"seed": 1101, "seeds": [1101, 1102, 1103, 1104], "performances": {}}
    m["body"]["runs"] = []
    implementation = set()
    for reader, p in m["performances"].items():
        for key in ["playback", "silence_spatial"]:
            p[key] = "../encounter-v2/" + p[key]
        records = {}
        for condition in ["sound", "silence"]:
            records[condition] = []
            for seed in [1101, 1102, 1103, 1104]:
                name = f"{reader}-{condition}-{seed}"
                r = json.loads((root / f"{name}.json").read_text())
                implementation.add(
                    json.dumps(r["provenance"].get("implementation_sha256"), sort_keys=True)
                )
                if not r["metrics"]["complete"]:
                    if not args.preview:
                        raise RuntimeError(f"Failed body run: {name}")
                    continue
                records[condition].append({"seed": seed, "metrics": r["metrics"]})
                artifact = out / f"{name}.json.gz"
                shutil.copy2(root / artifact.name, artifact)
                m["body"]["runs"].append(
                    {
                        "reader": reader,
                        "condition": condition,
                        "seed": seed,
                        "path": artifact.name,
                        "bytes": artifact.stat().st_size,
                        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    }
                )
                if seed == 1101:
                    p[f"{condition}_body"] = f"{name}.json.gz"
        if not all(f"{condition}_body" in p for condition in records):
            raise RuntimeError("The designated replay seed failed.")
        paired = set(r["seed"] for r in records["sound"]) & set(
            r["seed"] for r in records["silence"]
        )
        summary = {}
        for metric in [
            "distance_walked_cm",
            "flight_seconds",
            "turns_revolutions",
            "after_voice_distance_cm",
        ]:
            values = {
                c: {r["seed"]: r["metrics"][metric] for r in rows} for c, rows in records.items()
            }
            summary[metric] = {
                c: aggregate([v[s] for s in sorted(paired)]) for c, v in values.items()
            }
            summary[metric]["change"] = aggregate(
                [values["sound"][s] - values["silence"][s] for s in sorted(paired)]
            )
        report["performances"][reader] = {
            "summary": summary,
            "paired_seeds": sorted(paired),
            "runs": records,
        }
    if len(implementation) != 1 and not args.preview:
        raise RuntimeError(
            "Body runs use different implementation versions; rerun the full predefined batch."
        )
    report["qualified"] = not args.preview
    m["body"]["summary"] = "movement-summary.json"
    (out / "manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    (out / "movement-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    proof = Path("results/body-controller/combined/arena-proof.json.gz")
    if proof.exists():
        shutil.copy2(proof, out / "controller-proof.json.gz")
    print(out, "PREVIEW" if args.preview else "qualified")


if __name__ == "__main__":
    main()

"""Export an explicitly labeled static edition from a completed real reading."""

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = [
    "result.json",
    "audio.wav",
    "encoding.json",
    "reading-input.json",
    "spikes.npz",
    "populations.npz",
    "population_metrics.json",
    "METHOD.md",
]


def copy_record(source: Path, output: Path):
    result = json.loads((source / "result.json").read_text())
    if not result["fly"]["weights_unchanged"] or not result["timeline"]:
        raise ValueError("Only a completed frozen-connectome record can be published")
    if (
        result["display"]["poem"]
        != json.loads((ROOT / "examples/example.json").read_text())["poem"]
    ):
        raise ValueError("Only the designated public-domain opening poem may be exported")
    target = output / "recordings" / result["id"]
    target.mkdir(parents=True, exist_ok=True)
    for name in ARTIFACTS:
        shutil.copy2(source / name, target / name)
    for name in (
        "recording-source.json",
        "original.mp3",
        "silence-spikes.npz",
        "silence-populations.npz",
        "benchmark.json",
        "neural-display.json",
    ):
        if (source / name).exists():
            shutil.copy2(source / name, target / name)
    (target / "status.json").write_text(json.dumps({"status": "complete", "id": result["id"]}))
    return result


def export(source: Path, output: Path):
    shutil.copytree(ROOT / "static", output, dirs_exist_ok=True)
    primary = copy_record(source, output)
    performances = [
        {
            "id": primary["id"],
            "label": "01 / Synthetic reference",
            "description": "Kokoro af_sarah: the fixed synthetic reference. Each performance has its own response, silence control and interpretation.",
        }
    ]
    human = ROOT / "examples/blake-sayers"
    if (
        source.resolve() == (ROOT / "examples/blake-the-fly").resolve()
        and (human / "result.json").exists()
    ):
        result = copy_record(human, output)
        performances.append(
            {
                "id": result["id"],
                "label": "02 / Denny Sayers · human performance",
                "description": "Denny Sayers / LibriVox (2006). Poem-only excerpt, original pacing; normalized with the same RMS/peak rule. Approximate line timing is display-only. This compares performances, not semantic understanding.",
            }
        )
    (output / "site-config.json").write_text(
        json.dumps(
            {
                "mode": "recorded",
                "reading": primary["id"],
                "performances": performances,
                "example": json.loads((ROOT / "examples/example.json").read_text()),
            }
        )
    )
    shutil.copy2(ROOT / "docs/CRITICAL-DIRECTIONS.md", output / "CRITICAL-DIRECTIONS.md")
    (output / ".nojekyll").touch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "examples/blake-the-fly")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    export(args.source, args.output)

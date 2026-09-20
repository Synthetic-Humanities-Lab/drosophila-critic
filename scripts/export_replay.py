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


def export(source: Path, output: Path):
    result = json.loads((source / "result.json").read_text())
    if not result["fly"]["weights_unchanged"] or not result["timeline"]:
        raise ValueError("Only a completed frozen-connectome record can be published")
    if (
        result["display"]["poem"]
        != json.loads((ROOT / "examples/example.json").read_text())["poem"]
    ):
        raise ValueError("Only the designated public-domain opening poem may be exported")
    shutil.copytree(ROOT / "static", output, dirs_exist_ok=True)
    target = output / "recordings" / result["id"]
    target.mkdir(parents=True, exist_ok=True)
    for name in ARTIFACTS:
        shutil.copy2(source / name, target / name)
    (target / "status.json").write_text(json.dumps({"status": "complete", "id": result["id"]}))
    (output / "site-config.json").write_text(
        json.dumps(
            {
                "mode": "recorded",
                "reading": result["id"],
                "example": json.loads((ROOT / "examples/example.json").read_text()),
            }
        )
    )
    (output / ".nojekyll").touch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "examples/blake-the-fly")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    export(args.source, args.output)

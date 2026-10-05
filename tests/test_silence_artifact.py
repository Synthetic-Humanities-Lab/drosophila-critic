"""A stale control must fail CI rather than silently follow a changed simulator."""

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


def test_saved_silence_matches_implementation_and_lossless_chunks():
    directory = STATIC / "assets/silence-v1"
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["schema_version"] == "saved-silence-v1"
    assert manifest["contract"]["seed"] == 1101
    assert manifest["steps"] == 3230
    for name, expected in manifest["source_sha256"].items():
        assert hashlib.sha256((STATIC / name).read_bytes()).hexdigest() == expected, (
            f"Regenerate and verify saved silence after changing {name}"
        )
    start = 0
    for part in manifest["chunks"]:
        compressed = (directory / part["file"]).read_bytes()
        assert hashlib.sha256(compressed).hexdigest() == part["sha256"]
        assert len(compressed) == part["bytes"]
        raw = gzip.decompress(compressed)
        assert len(raw) == part["raw_bytes"]
        data = json.loads(raw)
        assert data["start"] == start == part["start"]
        assert len(data["counts"]) == len(data["firing_steps"]) == part["steps"]
        assert len(data["body"]["positions"]) == part["steps"]
        start += part["steps"]
    assert start == manifest["steps"]
    assert sum(part["bytes"] for part in manifest["chunks"]) == manifest["transfer_bytes"]
    assert not (directory / "body-reference.json").exists()
    assert not (directory / "neural-reference.json").exists()

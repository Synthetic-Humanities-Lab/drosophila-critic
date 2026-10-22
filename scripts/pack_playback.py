"""Lossless delivery copies; the recorded experiment files remain authoritative."""

import gzip
import hashlib
import json
import os
import struct
import sys
from array import array
from pathlib import Path

MAGIC = b"FLYBODY1"
FIELDS = ("time", "positions", "quaternions")


def pack_body(record: dict) -> bytes:
    """Shuffle IEEE-754 byte planes for gzip, without rounding or dropping frames."""
    metadata = {key: value for key, value in record.items() if key not in FIELDS}
    frames, bodies = len(record["time"]), len(record["body_names"])
    shapes = ([frames], [frames, bodies, 3], [frames, bodies, 4])
    blocks = []
    for field, shape in zip(FIELDS, shapes):
        values = record[field]
        if len(values) != frames:
            raise ValueError("Incomplete body recording")
        if len(shape) == 3:
            if any(len(row) != bodies or any(len(v) != shape[2] for v in row) for row in values):
                raise ValueError("Inconsistent body dimensions")
            values = (v for row in values for pose in row for v in pose)
        numbers = array("d", values)
        if sys.byteorder != "little":
            numbers.byteswap()
        raw = numbers.tobytes()
        blocks.append(b"".join(raw[byte::8] for byte in range(8)))
    header = json.dumps(
        {"record": metadata, "shapes": shapes}, separators=(",", ":"), allow_nan=False
    ).encode()
    return MAGIC + struct.pack("<I", len(header)) + header + b"".join(blocks)


def optimize_playback(site: Path) -> None:
    """Publish a separate delivery edition; older clients retain their manifest."""
    base = site / "experiments/encounter-v3"
    path = base / "manifest.json"
    manifest = json.loads(path.read_text())
    target = site / "experiments/encounter-v4"
    target.mkdir()
    manifest["schema_version"] = "encounter-manifest-v4"
    manifest["source_manifest"] = "../encounter-v3/manifest.json"
    body = manifest.get("body", {})
    if "summary" in body:
        body["summary"] = os.path.relpath(base / body["summary"], target)
    for run in body.get("runs", []):
        run["path"] = os.path.relpath(base / run["path"], target)
    delivery = {}
    for performance in manifest["performances"].values():
        for field in ("sound_body", "silence_body", "audio"):
            source = (base / performance[field]).resolve()
            if not source.is_relative_to(site.resolve()):
                raise ValueError("Playback source is outside the export")
            original = source.read_bytes()
            if field == "audio":
                raw, extension = original, "wav.gz"
            else:
                raw = pack_body(json.loads(gzip.decompress(original)))
                extension = "body.gz"
            compressed = gzip.compress(raw, compresslevel=9, mtime=0)
            digest = hashlib.sha256(compressed).hexdigest()
            name = f"{digest[:24]}.{extension}"
            (target / name).write_bytes(compressed)
            delivery[name] = {
                "source": os.path.relpath(source, target),
                "source_sha256": hashlib.sha256(original).hexdigest(),
                "sha256": digest,
                "bytes": len(compressed),
                "raw_bytes": len(raw),
                "format": "gzip-waveform" if field == "audio" else "flybody-float64-v1",
            }
            performance[field] = name
    manifest["delivery"] = {
        "description": "Lossless delivery copies. All recorded frames and float64 values retained.",
        "files": delivery,
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

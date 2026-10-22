import gzip
import json
import struct
import sys
from array import array
from pathlib import Path

import pytest

from scripts.pack_playback import FIELDS, MAGIC, optimize_playback, pack_body

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("reader", ["a", "b"])
@pytest.mark.parametrize("condition", ["sound", "silence"])
def test_every_recorded_float_and_metadata_survives_packing(reader, condition):
    original = ROOT / f"experiments/encounter-v3/{reader}-{condition}-1101.json.gz"
    record = json.loads(gzip.decompress(original.read_bytes()))
    packed = pack_body(record)
    assert packed[:8] == MAGIC
    size = struct.unpack_from("<I", packed, 8)[0]
    header = json.loads(packed[12 : 12 + size])
    assert header["record"] == {key: value for key, value in record.items() if key not in FIELDS}
    offset = 12 + size
    for field, shape in zip(FIELDS, header["shapes"], strict=True):
        values = record[field]
        if len(shape) == 3:
            values = [v for row in values for pose in row for v in pose]
        count = len(values)
        raw = bytearray(count * 8)
        for byte in range(8):
            raw[byte::8] = packed[offset + byte * count : offset + (byte + 1) * count]
        expected = array("d", values)
        if sys.byteorder != "little":
            expected.byteswap()
        assert raw == expected.tobytes()  # bit-exact, not a numerical tolerance
        offset += count * 8
    assert offset == len(packed)
    assert len(gzip.compress(packed, mtime=0)) < original.stat().st_size * 0.4


def test_delivery_keeps_source_recordings_and_audio_intact(tmp_path):
    base = tmp_path / "experiments/encounter-v3"
    base.mkdir(parents=True)
    body = dict(
        time=[0],
        body_names=["thorax"],
        positions=[[[1, 2, 3]]],
        quaternions=[[[1, 0, 0, 0]]],
        states=["standing"],
        airborne=[False],
        commands=[{}],
    )
    body_bytes = gzip.compress(json.dumps(body).encode(), mtime=0)
    audio_bytes = b"RIFF\x00\xffarbitrary exact waveform bytes"
    (base / "body.json.gz").write_bytes(body_bytes)
    (base / "audio.wav").write_bytes(audio_bytes)
    (base / "manifest.json").write_text(
        json.dumps(
            {
                "performances": {
                    "a": {
                        "audio": "audio.wav",
                        "sound_body": "body.json.gz",
                        "silence_body": "body.json.gz",
                    }
                }
            }
        )
    )
    original_manifest = (base / "manifest.json").read_bytes()
    optimize_playback(tmp_path)
    target = tmp_path / "experiments/encounter-v4"
    manifest = json.loads((target / "manifest.json").read_text())
    performance = manifest["performances"]["a"]
    assert gzip.decompress((target / performance["audio"]).read_bytes()) == audio_bytes
    assert (base / "manifest.json").read_bytes() == original_manifest
    assert (base / "audio.wav").read_bytes() == audio_bytes
    assert (base / "body.json.gz").read_bytes() == body_bytes
    assert len(manifest["delivery"]["files"]) == 2


def test_incomplete_body_cannot_be_published():
    with pytest.raises(ValueError, match="Incomplete"):
        pack_body(dict(time=[0, 1], body_names=["thorax"], positions=[], quaternions=[]))

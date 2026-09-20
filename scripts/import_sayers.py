"""Curated performance import. Requires optional `av==18.1.0`, not ASR at runtime."""

import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

import av
import numpy as np

from critic.example import EXAMPLE
from critic.pipeline import run_audio_reading, save_json
from critic.simulation import SimulationRunner

ROOT = Path(__file__).resolve().parents[1]


def main():
    meta = json.loads((ROOT / "examples/sayers-source.json").read_text())
    original = ROOT / "data/recordings/blake-fly-denny-sayers.mp3"
    original.parent.mkdir(parents=True, exist_ok=True)
    if not original.exists():
        urllib.request.urlretrieve(meta["download"], original)
    if hashlib.sha256(original.read_bytes()).hexdigest() != meta["source_sha256"]:
        raise ValueError("Source recording checksum changed")
    resampler = av.AudioResampler(format="fltp", layout="mono", rate=24000)
    parts = []
    with av.open(str(original)) as container:
        for frame in container.decode(audio=0):
            parts.extend(f.to_ndarray().reshape(-1) for f in resampler.resample(frame))
        parts.extend(f.to_ndarray().reshape(-1) for f in resampler.resample(None))
    samples = np.concatenate(parts)
    samples = samples[
        round(meta["clip_start_seconds"] * 24000) : round(meta["clip_end_seconds"] * 24000)
    ]
    target = ROOT / "results/blake-sayers-v1"
    voice = {
        "provider": "librivox-recording",
        "voice": "Denny Sayers",
        "speaking_rate": "original performance; unmodified",
        "pitch": "original performance; unmodified",
        "source": meta,
        "decoder": "PyAV 18.1.0; mono 24 kHz",
        "alignment": "approximate editorial timestamps; display only",
    }
    result = run_audio_reading(
        EXAMPLE,
        target,
        SimulationRunner(),
        samples,
        24000,
        meta["lines"],
        voice,
        lambda stage, value: (
            print(stage, round(value * 100), flush=True) if round(value * 100) % 25 == 0 else None
        ),
    )
    save_json(target / "recording-source.json", meta)
    shutil.copy2(original, target / "original.mp3")
    shutil.copytree(target, ROOT / "examples/blake-sayers", dirs_exist_ok=True)
    print(json.dumps(result["benchmark"]["global"]), flush=True)


if __name__ == "__main__":
    main()

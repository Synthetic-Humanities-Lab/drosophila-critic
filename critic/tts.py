"""Fixed, local eSpeak NG synthesis. Text stops at this boundary.

Each line is synthesized separately for measured (not guessed) line timing.
This deliberately imposes a uniform line break; see METHOD.md.
"""

import ctypes as C
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path
from typing import Protocol

import numpy as np

from .config import MAX_AUDIO_SECONDS


class TTSProvider(Protocol):
    def synthesize(self, poem: str, directory: Path) -> tuple[np.ndarray, int, list, dict]: ...


class EspeakProvider:
    """A fresh process isolates eSpeak's mutable global state on every run."""

    def synthesize(self, poem: str, directory: Path):
        subprocess.run(
            [sys.executable, "-m", "critic.tts", str(directory)],
            input=poem,
            text=True,
            check=True,
            capture_output=True,
            timeout=45,
        )
        with np.load(directory / "tts.npz", allow_pickle=False) as data:
            samples, rate = data["samples"].copy(), int(data["sample_rate"])
        metadata = json.loads((directory / "tts.json").read_text())
        return samples, rate, metadata.pop("lines"), metadata


def _synthesize(poem: str, directory: Path):
    import espeakng_loader

    library = Path(espeakng_loader.get_library_path())
    lib = C.CDLL(str(library))
    callback_type = C.CFUNCTYPE(C.c_int, C.POINTER(C.c_short), C.c_int, C.c_void_p)
    lib.espeak_Initialize.argtypes = [C.c_int, C.c_int, C.c_char_p, C.c_int]
    lib.espeak_Initialize.restype = C.c_int
    lib.espeak_SetVoiceByName.argtypes = [C.c_char_p]
    lib.espeak_SetParameter.argtypes = [C.c_int, C.c_int, C.c_int]
    lib.espeak_SetSynthCallback.argtypes = [callback_type]
    lib.espeak_Synth.argtypes = [
        C.c_void_p,
        C.c_size_t,
        C.c_uint,
        C.c_int,
        C.c_uint,
        C.c_uint,
        C.POINTER(C.c_uint),
        C.c_void_p,
    ]
    lib.espeak_Info.argtypes = [C.c_void_p]
    lib.espeak_Info.restype = C.c_char_p
    sample_rate = lib.espeak_Initialize(2, 0, espeakng_loader.get_data_path().encode(), 0)
    if sample_rate <= 0 or lib.espeak_SetVoiceByName(b"en-us") != 0:
        raise RuntimeError("The pinned eSpeak NG en-us voice could not be initialized")
    settings = {1: 165, 2: 100, 3: 50, 4: 50, 7: 0}
    for parameter, value in settings.items():
        if lib.espeak_SetParameter(parameter, value, 0) != 0:
            raise RuntimeError(f"eSpeak NG refused parameter {parameter}")
    buffers = []

    @callback_type
    def receive(wav, count, events):
        if wav and count:
            buffers.append(np.ctypeslib.as_array(wav, shape=(count,)).copy())
        return 0

    lib.espeak_SetSynthCallback(receive)
    pieces, lines, offset = [], [], 0
    gap = np.zeros(round(sample_rate * 0.18), dtype=np.float32)
    for number, line in enumerate(poem.splitlines(), 1):
        buffers.clear()
        if line.strip():
            encoded = line.encode("utf-8") + b"\0"
            # UTF-8 only: no SSML and no embedded phoneme-command mode.
            if lib.espeak_Synth(encoded, len(encoded), 0, 1, 0, 1, None, None) != 0:
                raise RuntimeError("eSpeak NG synthesis failed")
        pcm = (
            np.concatenate(buffers).astype(np.float32) / 32768
            if buffers
            else np.zeros(0, np.float32)
        )
        lines.append(
            {
                "line": number,
                "start": offset / sample_rate,
                "end": (offset + len(pcm)) / sample_rate,
            }
        )
        pieces.extend([pcm, gap])
        offset += len(pcm) + len(gap)
        if offset / sample_rate > MAX_AUDIO_SECONDS:
            raise ValueError(
                f"Synthesized audio exceeds the {MAX_AUDIO_SECONDS}-second prototype limit"
            )
    samples = np.concatenate(pieces)
    if not np.any(samples):
        raise ValueError("The supplied text produced no speech")
    lib.espeak_Terminate()
    voice_data = Path(espeakng_loader.get_data_path())
    voice_digest = hashlib.sha256()
    for resource in sorted(p for p in voice_data.rglob("*") if p.is_file()):
        voice_digest.update(str(resource.relative_to(voice_data)).encode() + b"\0")
        voice_digest.update(resource.read_bytes())
    metadata = {
        "provider": "espeak-ng-local",
        "voice": "en-us",
        "rate_wpm": 165,
        "pitch": 50,
        "pitch_range": 50,
        "volume": 100,
        "line_gap_seconds": 0.18,
        "version": lib.espeak_Info(None).decode(),
        "loader_version": importlib.metadata.version("espeakng-loader"),
        "library_sha256": hashlib.sha256(library.read_bytes()).hexdigest(),
        "voice_data_sha256": voice_digest.hexdigest(),
        "line_timing_method": "separate line synthesis; exact PCM boundaries; no forced alignment",
        "lines": lines,
    }
    np.savez(directory / "tts.npz", samples=samples, sample_rate=sample_rate)
    (directory / "tts.json").write_text(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    _synthesize(sys.stdin.read(), Path(sys.argv[1]))

"""Pinned local Kokoro voice. Its text/phonemes never leave the TTS boundary."""

import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from .config import DATA, MAX_AUDIO_SECONDS

MODEL_FILES = {
    "kokoro-v1.0.onnx": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
    "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}
VOICE = "af_sarah"
SPEED = 1.0


class KokoroProvider:
    def synthesize(self, poem: str, directory: Path):
        subprocess.run(
            [sys.executable, "-m", "critic.neural_tts", str(directory)],
            input=poem,
            text=True,
            check=True,
            capture_output=True,
            timeout=180,
        )
        with np.load(directory / "tts.npz", allow_pickle=False) as data:
            samples, rate = data["samples"].copy(), int(data["sample_rate"])
        metadata = json.loads((directory / "tts.json").read_text())
        return samples, rate, metadata.pop("lines"), metadata


def _synthesize(poem: str, directory: Path):
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    from kokoro_onnx.config import MAX_PHONEME_LENGTH

    for name, digest in MODEL_FILES.items():
        path = DATA / "tts" / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("The fixed voice is missing or changed. Run scripts/setup_voice.py.")
    ort.disable_telemetry_events()
    ort.set_seed(64)
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    session = ort.InferenceSession(
        str(DATA / "tts" / "kokoro-v1.0.onnx"), options, providers=["CPUExecutionProvider"]
    )

    class FloatSpeedSession:
        _model_path = str(DATA / "tts" / "kokoro-v1.0.onnx")

        # kokoro-onnx 0.4.9 sends int32 speed for input_ids exports. This
        # pinned model declares float32; adapt only that transport dtype.
        def get_inputs(self):
            return session.get_inputs()

        def run(self, outputs, inputs):
            return session.run(
                outputs, {**inputs, "speed": np.asarray(inputs["speed"], dtype=np.float32)}
            )

    engine = Kokoro.from_session(FloatSpeedSession(), str(DATA / "tts" / "voices-v1.0.bin"))
    sample_rate = 24000
    pieces, lines, offset = [], [], 0
    gap = np.zeros(round(sample_rate * 0.18), dtype=np.float32)
    for number, line in enumerate(poem.splitlines(), 1):
        pcm = np.zeros(0, dtype=np.float32)
        if line.strip():
            phonemes = engine.tokenizer.phonemize(line, "en-us")
            # The upstream engine truncates oversized unbroken phoneme batches.
            # Reject those instead of silently dropping part of the poem.
            if any(len(batch) > MAX_PHONEME_LENGTH for batch in engine._split_phonemes(phonemes)):
                raise ValueError(
                    "A line exceeds the voice's pronunciation limit. Add a line break."
                )
            if phonemes.strip():
                pcm, rate = engine.create(
                    phonemes, VOICE, SPEED, "en-us", is_phonemes=True, trim=True
                )
                if rate != sample_rate:
                    raise RuntimeError("The pinned voice changed its sample rate")
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
    samples = np.concatenate(pieces).astype(np.float32)
    if not np.any(samples):
        raise ValueError("The supplied text produced no speech")
    np.savez(directory / "tts.npz", samples=samples, sample_rate=sample_rate)
    metadata = {
        "provider": "kokoro-onnx",
        "provider_version": importlib.metadata.version("kokoro-onnx"),
        "model": "Kokoro v1.0 (82M)",
        "voice": VOICE,
        "language": "en-us",
        "speed": SPEED,
        "pitch": "native fixed voice; no pitch shift",
        "line_gap_seconds": 0.18,
        "line_synthesis": "independent lines; upstream silence trim enabled",
        "model_sha256": MODEL_FILES,
        "execution_provider": "CPUExecutionProvider",
        "tts_seed": 64,
        "speed_transport_adapter": "int32 to model-declared float32 (kokoro-onnx 0.4.9)",
        "onnxruntime_version": ort.__version__,
        "intra_op_threads": 4,
        "inter_op_threads": 1,
        "lines": lines,
    }
    (directory / "tts.json").write_text(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    _synthesize(sys.stdin.read(), Path(sys.argv[1]))

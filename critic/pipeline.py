import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .audio_encoder import EAR_CAP, VERSION, VOLTAGE_GAIN, encode, preprocess, write_wav
from .config import DT, MAX_AUDIO_SECONDS, MAX_CHARACTERS, ROOT
from .example import EXAMPLE  # noqa: F401 — retained for existing validation imports
from .interpretation import interpret, summarize_response
from .neural_tts import KokoroProvider
from .response import analyze


def save_json(path: Path, value):
    temporary = path.with_suffix(".json.part")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def validate_poem(poem: str):
    if not poem.strip() or len(poem) > MAX_CHARACTERS or "\0" in poem:
        raise ValueError(f"Enter a poem of 1–{MAX_CHARACTERS} characters without null bytes")
    if len(poem.splitlines()) > 80:
        raise ValueError("The prototype accepts at most 80 lines")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in poem):
        raise ValueError("The poem contains unsupported control characters")


def run_reading(poem: str, directory: Path, runner, progress=lambda *_: None, tts=None):
    validate_poem(poem)
    directory.mkdir(parents=True, exist_ok=True)
    poem_id = hashlib.sha256(poem.encode()).hexdigest()
    progress("SYNTHESIZING VOICE", 0)
    samples, sample_rate, lines, voice = (tts or KokoroProvider()).synthesize(poem, directory)
    duration = len(samples) / sample_rate
    if duration > MAX_AUDIO_SECONDS:
        raise ValueError(f"Audio exceeds the {MAX_AUDIO_SECONDS}-second prototype limit")
    progress("TRANSDUCING AUDIO", 0)
    samples, normalization = preprocess(samples)
    digest = write_wav(directory / "audio.wav", samples, sample_rate)
    frames = encode(samples, sample_rate)
    encoding = {
        "version": VERSION,
        "timestep": DT,
        "sample_rate": sample_rate,
        "mapping": "min(4 * frame RMS, 0.8) equally into upstream ear_cells",
        "voltage_gain": VOLTAGE_GAIN,
        "cap": EAR_CAP,
        "frames": frames,
    }
    save_json(directory / "encoding.json", encoding)
    progress("READING", 0)
    record = runner.run(frames, directory, progress)
    progress("MEASURING RESPONSE", 0)
    response, timeline, populations, population_timeline = analyze(record, frames, lines)
    save_json(directory / "population_metrics.json", populations)
    progress("INTERPRETING RESPONSE", 0)
    summary = summarize_response(response)
    # This is the complete, separately saved interpretation input. No poem/line text.
    save_json(directory / "reading-input.json", summary.model_dump())
    reading = interpret(summary)
    source_hashes = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "critic").glob("*.py"))
    }
    result = {
        "schema_version": "1.0",
        "id": directory.name,
        "poem_id": poem_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "audio": {
            **voice,
            "duration": duration,
            "sample_rate": sample_rate,
            "sha256": digest,
            "normalization": normalization,
            "encoder_version": VERSION,
        },
        "fly": record["fly"],
        "encoder": {k: v for k, v in encoding.items() if k != "frames"},
        "timeline": timeline,
        "population_timeline": population_timeline,
        "response": response,
        "reading": reading,
        "provenance": {
            "application_source_sha256": source_hashes,
            "method_sha256": hashlib.sha256((ROOT / "METHOD.md").read_bytes()).hexdigest(),
            "simulation_input": "normalized PCM-derived RMS frames only",
            "interpretation_input": "reading-input.json only",
            "raw_spikes": "spikes.npz",
            "population_counts": "populations.npz",
            "all_population_metrics": "population_metrics.json",
            "injections": "encoding.json",
        },
        "display": {
            "poem": poem,
            "lines": lines,
            "note": "Display-only text. Never passed to simulator or interpreter.",
        },
    }
    (directory / "METHOD.md").write_text((ROOT / "METHOD.md").read_text())
    save_json(directory / "result.json", result)
    return result

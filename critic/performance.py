"""Paired waveform experiment using the existing receiver and frozen simulator."""

import hashlib
import io
import math
import wave
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

from .audio_encoder import VERSION, encode
from .config import DT, ROOT
from .delivery import equalize, paired_stats
from .performance_passages import passage_report, validate_input_correspondence, validate_windows
from .performance_reading import ComparisonSummary, interpret_comparison
from .pipeline import save_json

RATE = 48_000
MAX_SECONDS = 120
MAX_FILE_BYTES = 12_000_000
SEEDS = (1101, 1102, 1103, 1104)
TAIL_SECONDS = 3.0
GROUPS = (
    "JO-A/B input",
    "direct JON postsynaptic partners",
    "descending_neuron",
    "wing motor (flytalk WING_MN)",
)


def decode_upload(content: bytes):
    if not content or len(content) > MAX_FILE_BYTES:
        raise ValueError("Each decoded WAV must be between 1 byte and 12 MB")
    try:
        with wave.open(io.BytesIO(content), "rb") as source:
            rate, count, channels = (
                source.getframerate(),
                source.getnframes(),
                source.getnchannels(),
            )
            if source.getsampwidth() != 2 or channels not in (1, 2):
                raise ValueError("Upload mono or stereo PCM16 WAV")
            if not 8000 <= rate <= 96000 or not 0 < count <= rate * MAX_SECONDS:
                raise ValueError("Recordings must be nonempty, at most 120 seconds, 8–96 kHz")
            raw = source.readframes(count)
            if len(raw) != count * channels * 2:
                raise ValueError("Truncated WAV audio")
    except (wave.Error, EOFError) as error:
        raise ValueError("Invalid PCM WAV recording") from error
    samples = np.frombuffer(raw, "<i2").astype(float).reshape(-1, channels).mean(axis=1) / 32768
    if rate != RATE:
        divisor = math.gcd(rate, RATE)
        samples = resample_poly(samples, RATE // divisor, rate // divisor)
    if not np.any(samples):
        raise ValueError("A performance is silent after channel averaging; choose audible audio")
    return samples, {
        "sha256": hashlib.sha256(content).hexdigest(),
        "sample_rate": rate,
        "channels": channels,
        "duration": count / rate,
        "resampled_rate": RATE,
        "resampling": "scipy.signal.resample_poly" if rate != RATE else None,
    }


def save_pcm(path, samples):
    # equalize already quantized; recover that exact PCM, without a second gain.
    pcm = np.rint(samples * 32768).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, RATE, len(pcm), "NONE", "not compressed"))
        output.writeframes(pcm.tobytes())
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _bins(values, width=5):
    return np.array([values[i : i + width].mean(axis=0) for i in range(0, len(values), width)])


def measure(record, control):
    indices = [record["group_names"].index(name) for name in GROUPS]
    sizes = np.asarray(record["group_sizes"])[indices]
    if np.any(sizes <= 0):
        raise ValueError("A required annotated population is absent")
    raw = record["group_counts"][:, indices].astype(float) / sizes / DT
    silence = control["group_counts"][:, indices].astype(float) / sizes / DT
    corrected = raw - silence
    phase = record["phase"]
    # Timeline includes baseline and persistence; bin edges relative to sound onset.
    start = record["before"] - round(1 / DT)
    return {
        "baseline": raw[phase == "baseline"].mean(axis=0),
        "raw_rate": raw[phase == "audio"].mean(axis=0),
        "silence_rate": silence[phase == "audio"].mean(axis=0),
        "rate": corrected[phase == "audio"].mean(axis=0),
        "tail": corrected[phase == "tail"].mean(axis=0),
        "timeline": _bins(corrected[start:]),
        "raw_timeline": _bins(raw[start:]),
        "audio_timeline": _bins(corrected[phase == "audio"]),
        "audio_rates": corrected[phase == "audio"],
        "types": (
            record["phase_type_counts"][1].astype(float)
            - control["phase_type_counts"][1].astype(float)
        )
        / record["type_sizes"]
        / (np.count_nonzero(phase == "audio") * DT),
    }


def analyze_pair(measurements, durations, type_names):
    performances, differences = {}, []
    for name, rows in measurements.items():
        traces = np.stack([row["timeline"] for row in rows])
        raw_traces = np.stack([row["raw_timeline"] for row in rows])
        populations = []
        for j, group in enumerate(GROUPS):
            populations.append(
                {
                    "population": group,
                    **{
                        metric: paired_stats([row[metric][j] for row in rows])
                        for metric in ("baseline", "raw_rate", "silence_rate", "rate", "tail")
                    },
                }
            )
        performances[name] = {
            "populations": populations,
            "timeline": {
                "start_seconds": -1.0,
                "bin_seconds": 0.1,
                "mean": traces.mean(axis=0).tolist(),
                "sd": traces.std(axis=0, ddof=1).tolist(),
                "raw_mean": raw_traces.mean(axis=0).tolist(),
            },
        }
    a, b = measurements["a"], measurements["b"]
    # Exclude partial last bins: unequal coverage must not be treated as equal time.
    overlap = math.floor(min(durations) / 0.1 + 1e-9)
    for j, group in enumerate(GROUPS):
        delta = np.stack(
            [
                y["audio_timeline"][:overlap, j] - x["audio_timeline"][:overlap, j]
                for x, y in zip(a, b, strict=True)
            ]
        )
        mean, sd = delta.mean(axis=0), delta.std(axis=0, ddof=1)
        differences.append(
            {
                "population": group,
                "rate": paired_stats([y["rate"][j] - x["rate"][j] for x, y in zip(a, b)]),
                "tail": paired_stats([y["tail"][j] - x["tail"][j] for x, y in zip(a, b)]),
                "temporal_separation_rms": float(np.sqrt(np.mean(mean**2))),
                "temporal_variability_rms": float(np.sqrt(np.mean(sd**2))),
                "peak_separation_seconds": float(np.argmax(np.abs(mean)) * 0.1),
                "paired_timeline_mean": mean.tolist(),
                "paired_timeline_sd": sd.tolist(),
            }
        )
    type_delta = np.stack([y["types"] - x["types"] for x, y in zip(a, b)])
    ranking = np.argsort(-np.abs(type_delta.mean(axis=0)))[:12]
    exploratory = [
        {"cell_type": str(type_names[i]), "difference": paired_stats(type_delta[:, i])}
        for i in ranking
        if str(type_names[i])
    ]
    return {
        "units": "spikes/second/neuron",
        "direction": "B minus A, each minus its duration-matched silence",
        "groups": list(GROUPS),
        "performances": performances,
        "differences": differences,
        "overlap_seconds": round(overlap * 0.1, 6),
        "exploratory_cell_types": exploratory,
        "exploratory_warning": "Largest absolute mean differences selected after measurement; no multiplicity correction or behavioral inference.",
        "bands": "sample standard deviation across four paired seeds; not confidence intervals",
    }


def run_comparison(contents, display, directory, runner, progress=lambda *_: None):
    directory.mkdir(parents=True, exist_ok=True)
    implementation = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in (
            "critic/performance.py",
            "critic/performance_reading.py",
            "critic/performance_passages.py",
            "critic/audio_encoder.py",
            "critic/delivery.py",
            "critic/simulation.py",
        )
    }
    progress("MATCHING RECORDING LEVELS", 0)
    decoded, audio = {}, {}
    for name in ("a", "b"):
        decoded[name], audio[name] = decode_upload(contents[name])
        if len(decoded[name]) < RATE:
            raise ValueError("Each performance must be at least one second")
        (directory / f"original-{name}.wav").write_bytes(contents[name])
    passages = display.get("passages", [])
    validate_windows(passages, {name: audio[name]["duration"] for name in audio})
    waves, levels = equalize(decoded)
    frames = {name: encode(waves[name], RATE) for name in waves}
    validate_input_correspondence(frames, passages)
    measurements = {"a": [], "b": []}
    runs = []
    for name in waves:
        audio[name].update(
            {
                "normalization": levels[name],
                "processed_sha256": save_pcm(directory / f"{name}.wav", waves[name]),
                "simulation_audio_seconds": len(frames[name]) * DT,
                "mean_injected_voltage": float(
                    np.mean([f["injected_voltage"] for f in frames[name]])
                ),
                "integrated_injected_voltage_seconds": float(
                    sum(f["injected_voltage"] for f in frames[name]) * DT
                ),
                "capped_frames": sum(f["injected_voltage"] >= 0.8 for f in frames[name]),
            }
        )
    save_json(directory / "encoding.json", {"version": VERSION, "frames": frames})
    completed, total = 0, len(SEEDS) * 4
    for seed in SEEDS:
        for name in ("a", "b"):
            records = []
            for condition in ("sound", "silence"):
                run_name = f"{name}-{condition}-{seed}"
                target = directory / run_name
                target.mkdir()
                stimulus = (
                    frames[name]
                    if condition == "sound"
                    else [{"injected_voltage": 0.0} for _ in frames[name]]
                )

                def report(_stage, fraction, label=run_name, done=completed):
                    progress(f"SIMULATING {label.upper()}", (done + fraction) / total * 0.96)

                record = runner.run(stimulus, target, report, seed=seed, tail_seconds=TAIL_SECONDS)
                save_json(target / "provenance.json", record["fly"])
                runs.append({"id": run_name, "fly": record["fly"]})
                records.append(record)
                completed += 1
            measurements[name].append(measure(*records))
    progress("COMPARING RESPONSES", 0.97)
    durations = [audio[name]["duration"] for name in ("a", "b")]
    response = analyze_pair(measurements, durations, records[0]["type_names"])
    response["passage_comparison"] = passage_report(
        measurements, frames, passages, dict(zip(("a", "b"), durations)), GROUPS
    )
    summary = ComparisonSummary(
        durations=durations,
        seeds=list(SEEDS),
        passages=[
            {
                "number": p["number"],
                "durations": [p["performances"][n]["duration"] for n in ("a", "b")],
                "mean_drives": [p["performances"][n]["mean_drive"] for n in ("a", "b")],
                "direct_rate_difference": p["populations"][1]["difference"]["mean"],
                "seed_differences": p["populations"][1]["difference"]["values"],
                "boundary_direction_consistent": p["populations"][1][
                    "same_direction_across_seeds_and_boundaries"
                ],
            }
            for p in response["passage_comparison"]["passages"]
        ],
        differences=[
            {
                "population": row["population"],
                "mean_rate_difference": row["rate"]["mean"],
                "seed_differences": row["rate"]["values"],
                "persistence_difference": row["tail"]["mean"],
                "temporal_separation_rms": row["temporal_separation_rms"],
                "temporal_variability_rms": row["temporal_variability_rms"],
            }
            for row in response["differences"]
        ],
    )
    save_json(directory / "reading-input.json", summary.model_dump())
    progress("INTERPRETING RESPONSE", 0.99)
    result = {
        "schema_version": "performance-comparison-v1",
        "id": directory.name,
        "display": display,
        "poem_id": hashlib.sha256(display["poem"].encode()).hexdigest(),
        "audio": audio,
        "encoder": VERSION,
        "implementation_sha256": implementation,
        "seeds": list(SEEDS),
        "tail_seconds": TAIL_SECONDS,
        "runs": runs,
        "response": response,
        "reading": {
            "provider": "response-only-template-v2",
            "input_summary": summary.model_dump(),
            "text": interpret_comparison(summary),
        },
        "limitations": [
            "Uncalibrated amplitude receiver; not a physiological model of the whole fly ear.",
            "No automatic word matching or line alignment; elapsed-time differences may reflect different passages.",
            "Equal whole-file RMS does not equalize duration, pauses, framewise drive or total exposure.",
            "Four seeds describe model variability, not biological variation or confirmatory significance.",
            "No motor behavior or subjective experience is inferred from population rates.",
        ],
    }
    save_json(directory / "result.json", result)
    progress("READY FOR COMPARISON", 1)
    return result

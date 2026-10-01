"""Minimum transduction v1. This module accepts waveform arrays, never text."""

import hashlib
import wave
from pathlib import Path

import numpy as np

from .config import DT

VERSION = "rms-jon-v1"
TARGET_RMS = 0.1
PEAK_LIMIT = 0.95
VOLTAGE_GAIN = 4.0
EAR_CAP = 0.8


def preprocess(samples: np.ndarray) -> tuple[np.ndarray, dict]:
    samples = np.asarray(samples, dtype=np.float64)
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    if samples.ndim != 1 or not len(samples) or not np.all(np.isfinite(samples)):
        raise ValueError("Audio must be a nonempty finite mono or samples-by-channels array")
    rms = float(np.sqrt(np.mean(samples**2)))
    peak = float(np.max(np.abs(samples)))
    gain = min(TARGET_RMS / rms, PEAK_LIMIT / peak) if peak > 0 else 1.0
    # Quantize once: the encoder and playback use exactly the same PCM samples.
    pcm = np.rint(samples * gain * 32767).astype(np.int16)
    normalized = pcm.astype(np.float32) / 32768
    return normalized, {
        "method": "whole-waveform RMS, peak-limited linear gain; PCM16 quantization",
        "target_rms": TARGET_RMS,
        "peak_limit": PEAK_LIMIT,
        "input_rms": rms,
        "gain": gain,
        "output_rms": float(np.sqrt(np.mean(normalized.astype(float) ** 2))),
        "output_peak": float(np.max(np.abs(normalized))),
        "silence_preserved": True,
    }


def encode(samples: np.ndarray, sample_rate: int, dt: float = DT) -> list[dict]:
    if samples.ndim != 1 or not len(samples) or sample_rate <= 0 or dt <= 0:
        raise ValueError("Expected mono PCM and positive sample rate/timestep")
    frame_samples = round(sample_rate * dt)
    if frame_samples < 1 or not np.isclose(frame_samples, sample_rate * dt):
        raise ValueError("Sample rate must permit exact timestep-aligned frames")
    frames = []
    for i, start in enumerate(range(0, len(samples), frame_samples)):
        part = samples[start : start + frame_samples].astype(np.float64)
        rms = float(np.sqrt(np.sum(part**2) / frame_samples))
        frames.append(
            {
                "step": i,
                "time": round(i * dt, 6),
                "sample_start": start,
                "sample_end": start + len(part),
                "padded_samples": frame_samples - len(part),
                "rms": rms,
                "injected_voltage": min(VOLTAGE_GAIN * rms, EAR_CAP),
            }
        )
    return frames


def write_wav(path: Path, samples: np.ndarray, sample_rate: int):
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(np.rint(samples * 32768).astype("<i2").tobytes())
    return hashlib.sha256(path.read_bytes()).hexdigest()

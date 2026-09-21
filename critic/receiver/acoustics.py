"""Waveform-only virtual acoustic calibration, independent of antennal mechanics."""

from dataclasses import asdict, dataclass
from math import gcd

import numpy as np
from scipy.signal import resample_poly


@dataclass(frozen=True)
class ReceiverConfig:
    sample_rate: int = 48000
    reference_digital_rms: float = 0.1
    reference_velocity_mm_s_rms: float = 0.5
    reference_frequency_hz: float = 200.0
    azimuth_degrees: float = 0.0

    def __post_init__(self):
        if self.sample_rate != 48000:
            raise ValueError("This receiver edition uses 48000 Hz processing")
        values = list(asdict(self).values())
        if not np.all(np.isfinite(values)):
            raise ValueError("Receiver configuration must be finite")
        if not 0 < self.reference_digital_rms <= 1 / np.sqrt(2):
            raise ValueError("Reference RMS must permit an unclipped sine")
        if self.reference_velocity_mm_s_rms <= 0 or self.reference_frequency_hz != 200:
            raise ValueError("Positive velocity and the 200 Hz reference are required")
        if not -180 <= self.azimuth_degrees <= 180:
            raise ValueError("Azimuth must be between -180 and 180 degrees")


def prepare_waveform(samples, source_rate, config=ReceiverConfig()):
    """Resample once; never normalize or compress a performance here."""
    x = np.asarray(samples, dtype=np.float64)
    if x.ndim == 2 and x.shape[1] > 0:
        x = x.mean(axis=1)
    if x.ndim != 1 or not len(x) or not np.all(np.isfinite(x)):
        raise ValueError("Expected nonempty finite mono or samples-by-channels audio")
    if not isinstance(source_rate, (int, np.integer)) or source_rate <= 0:
        raise ValueError("Sample rate must be a positive integer")
    if np.max(np.abs(x)) > 1:
        raise ValueError("Expected PCM scaled to [-1, 1]")
    divisor = gcd(source_rate, config.sample_rate)
    processed = resample_poly(x, config.sample_rate // divisor, source_rate // divisor)
    return processed, {
        "source_sample_rate_hz": int(source_rate),
        "processing_sample_rate_hz": config.sample_rate,
        "source_samples": len(x),
        "processed_samples": len(processed),
        "source_duration_seconds": len(x) / source_rate,
        "processed_duration_seconds": len(processed) / config.sample_rate,
        "linear_gain": 1.0,
        "normalization": "none; retain prior whole-recording level matching",
        "resampling": "scipy.signal.resample_poly, default Kaiser window",
        "processed_peak": float(np.max(np.abs(processed))),
    }


def particle_velocity(samples, config=ReceiverConfig()):
    """Assumed local plane-wave field; not a recovered recording pressure field."""
    x = np.asarray(samples, dtype=np.float64)
    if x.ndim != 1 or not np.all(np.isfinite(x)):
        raise ValueError("Expected finite mono samples")
    scalar = x * config.reference_velocity_mm_s_rms / config.reference_digital_rms
    angle = np.deg2rad(config.azimuth_degrees)
    return scalar[:, None] * np.array([np.cos(angle), np.sin(angle)])[None, :]


def project_axes(field, axes_degrees):
    """Explicit geometric projection; axis angles are caller assumptions, not fitted data."""
    field = np.asarray(field, dtype=float)
    axes = np.asarray(axes_degrees, dtype=float)
    if field.ndim != 2 or field.shape[1] != 2 or axes.shape != (2,):
        raise ValueError("Expected XY field and two antenna projection axes")
    if not np.all(np.isfinite(field)) or not np.all(np.isfinite(axes)):
        raise ValueError("Field and axes must be finite")
    angles = np.deg2rad(axes)
    return field @ np.array([np.cos(angles), np.sin(angles)])

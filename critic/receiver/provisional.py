"""Engineering-only mechanical envelope adapter; never production calibration."""

import numpy as np

from critic.audio_encoder import encode
from critic.receiver.acoustics import particle_velocity, prepare_waveform
from critic.receiver.healthy import SoundTransfer

VERSION = "mechanical-envelope-sensitivity-v1"


def encode_provisional(samples, sample_rate, quantity, strength):
    if quantity not in ("displacement", "velocity", "legacy"):
        raise ValueError("Choose displacement, velocity or legacy")
    if not np.isfinite(strength) or strength <= 0:
        raise ValueError("Strength must be finite and positive")
    waveform, preprocessing = prepare_waveform(samples, sample_rate)
    # Align the end of sound before adding the same five decay frames to every arm.
    padding = (-len(waveform)) % 960
    padded = np.pad(waveform, (0, padding + 4800))
    model = SoundTransfer()
    reference_velocity = abs(model.velocity_transfer(200)) * 0.5 * 1e6
    reference = reference_velocity / (2 * np.pi * 200)
    if quantity == "legacy":
        equivalent = padded
        reference = 0.1
    else:
        motion = model.process(particle_velocity(padded)[:, 0])
        if quantity == "velocity":
            reference = reference_velocity
        equivalent = motion[:, 0 if quantity == "displacement" else 1] / reference * 0.1
    # Scale before the inherited cap, not after clipping.
    frames = encode(equivalent * strength, 48000)
    return frames, {
        "version": VERSION,
        "physiologically_calibrated": False,
        "quantity": quantity,
        "strength": strength,
        "reference_response": float(reference),
        "reference_units": {"legacy": "digital", "displacement": "nm", "velocity": "nm/s"}[
            quantity
        ],
        "reference": "200 Hz digital RMS 0.1 -> 0.4 abstract voltage at unit strength",
        "preprocessing": preprocessing,
        "sound_frames": (len(waveform) + padding) // 960,
        "decay_frames": 5,
        "capped_frames": sum(f["injected_voltage"] >= 0.8 for f in frames),
        "integrated_drive": float(sum(f["injected_voltage"] for f in frames) * 0.02),
    }

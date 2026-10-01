"""User-timed corresponding passages; annotations never alter neural stimulation."""

from itertools import product

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import DT
from .delivery import paired_stats


class Window(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    start: float = Field(ge=0, le=120)
    end: float = Field(gt=0, le=120)

    @model_validator(mode="after")
    def positive_duration(self):
        if self.end - self.start < 0.2 - 1e-9:
            raise ValueError("Each passage must span at least 0.2 seconds")
        return self


class MatchedPassage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    a: Window
    b: Window


def validate_windows(passages, durations):
    previous = {"a": 0.0, "b": 0.0}
    if len(passages) > 20:
        raise ValueError("Use at most twenty corresponding passages")
    for passage in passages:
        value = MatchedPassage.model_validate(passage)
        for name in ("a", "b"):
            window = getattr(value, name)
            if window.start < previous[name] or window.end > durations[name] + 1e-9:
                raise ValueError(
                    "Passages must be ordered, nonoverlapping, and inside each recording"
                )
            previous[name] = window.end


def frame_window(window, length, start_shift=0.0, end_shift=0.0):
    start = max(0, round((window["start"] + start_shift) / DT))
    end = min(length, round((window["end"] + end_shift) / DT))
    if end <= start:
        return None
    return start, end


def validate_input_correspondence(frames, passages):
    drives = {name: np.array([f["injected_voltage"] for f in frames[name]]) for name in ("a", "b")}
    if np.array_equal(drives["a"], drives["b"]) and any(p["a"] != p["b"] for p in passages):
        raise ValueError(
            "Identical injected inputs require identical passage windows; different cuts alone would manufacture a comparison"
        )


def passage_report(measurements, frames, passages, durations, groups):
    validate_windows(passages, durations)
    drives = {name: np.array([f["injected_voltage"] for f in frames[name]]) for name in ("a", "b")}
    validate_input_correspondence(frames, passages)
    rates = {
        name: np.stack([row["audio_rates"] for row in measurements[name]]) for name in ("a", "b")
    }
    output = []
    for number, passage in enumerate(passages, 1):
        performances, alternatives = {}, {}
        for name in ("a", "b"):
            start, end = frame_window(passage[name], len(drives[name]))
            means = rates[name][:, start:end].mean(axis=1)
            performances[name] = {
                "requested_window": passage[name],
                "start": start * DT,
                "end": end * DT,
                "duration": (end - start) * DT,
                "mean_drive": float(drives[name][start:end].mean()),
                "integrated_drive": float(drives[name][start:end].sum() * DT),
                "rates_by_seed": means.tolist(),
                "net_spikes_per_neuron_by_seed": (means * (end - start) * DT).tolist(),
            }
            alternatives[name] = []
            for shift_start, shift_end in product((-0.1, 0.0, 0.1), repeat=2):
                window = frame_window(passage[name], len(drives[name]), shift_start, shift_end)
                if window is not None:
                    a, b = window
                    alternatives[name].append(rates[name][:, a:b].mean(axis=1))
        changes = (
            np.asarray(performances["b"]["rates_by_seed"]) - performances["a"]["rates_by_seed"]
        )
        boundary_deltas = np.stack(
            [b - a for a, b in product(alternatives["a"], alternatives["b"])]
        )
        populations = []
        for j, group in enumerate(groups):
            stats = paired_stats(changes[:, j])
            direction = np.sign(stats["mean"])
            populations.append(
                {
                    "population": group,
                    "difference": stats,
                    "same_direction_across_seeds_and_boundaries": bool(
                        direction != 0 and np.all(boundary_deltas[:, :, j] * direction > 1e-12)
                    ),
                    "boundary_mean_range": [
                        float(boundary_deltas[:, :, j].mean(axis=1).min()),
                        float(boundary_deltas[:, :, j].mean(axis=1).max()),
                    ],
                }
            )
        output.append(
            {
                "number": number,
                "performances": performances,
                "populations": populations,
                "valid_boundary_combinations": len(boundary_deltas),
            }
        )
    return {
        "passages": output,
        "method": "User-supplied correspondence; each interval snapped to nearest 20 ms frame. No time warping or transcription. Each rate is corrected by same-seed silence at that recording's own time.",
        "boundary_check": "Independently shift each of the four boundaries by -0.1, 0, +0.1 seconds (up to 81 combinations). Clip to recording frames and omit empty intervals. Direction consistency is descriptive, not statistical significance or validation of the alignment.",
        "selection": "Passages are user selected; no multiple-comparison correction. Duration, internal timing and input strength remain uncontrolled within passages.",
    }

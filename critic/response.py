"""Measurements from recorded spikes. No text, semantic labels, or learned readout."""

import numpy as np

from .config import BASELINE_SECONDS, DT, TAIL_SECONDS


def smooth(values, width=5):
    values = np.asarray(values, dtype=float)
    sums = np.cumsum(np.r_[0, values])
    return (
        sums[np.arange(len(values)) + 1] - sums[np.maximum(0, np.arange(len(values)) + 1 - width)]
    ) / np.minimum(np.arange(len(values)) + 1, width)


def analyze(record: dict, frames: list[dict], line_intervals: list[dict]):
    n = record["fly"]["neurons"]
    phase = record["phase"]
    audio = phase == "audio"
    baseline = phase == "baseline"
    tail = phase == "tail"
    before = record["before"]
    rates = record["counts"].astype(float) / (n * DT)
    filtered = smooth(rates)
    base = float(rates[baseline].mean())
    base_sd = float(filtered[baseline].std())
    delta = filtered - base
    threshold = max(3 * base_sd, 0.02)
    peak = before + int(np.argmax(np.abs(delta[audio])))
    durations = [BASELINE_SECONDS, len(frames) * DT, TAIL_SECONDS]
    populations = []
    for j, name in enumerate(record["type_names"]):
        if not str(name).strip():
            continue
        size = int(record["type_sizes"][j])
        values = record["phase_type_counts"][:, j] / (size * np.array(durations))
        populations.append(
            {
                "name": str(name),
                "kind": "annotated cell type",
                "neurons": size,
                "baseline_hz_per_neuron": float(values[0]),
                "audio_hz_per_neuron": float(values[1]),
                "tail_hz_per_neuron": float(values[2]),
                "delta_hz_per_neuron": float(values[1] - values[0]),
            }
        )
    by_change = sorted(populations, key=lambda p: (-abs(p["delta_hz_per_neuron"]), p["name"]))[:20]
    by_activity = sorted(populations, key=lambda p: (-p["audio_hz_per_neuron"], p["name"]))[:20]
    monitored = []
    for j, name in enumerate(record["group_names"]):
        size = record["group_sizes"][j]
        if not size:
            monitored.append({"name": name, "neurons": 0, "available": False})
            continue
        r = record["group_counts"][:, j] / (size * DT)
        monitored.append(
            {
                "name": name,
                "neurons": size,
                "available": True,
                "baseline_hz_per_neuron": float(r[baseline].mean()),
                "audio_hz_per_neuron": float(r[audio].mean()),
                "tail_hz_per_neuron": float(r[tail].mean()),
                "delta_hz_per_neuron": float(r[audio].mean() - r[baseline].mean()),
            }
        )

    def line_at(t):
        return next((row["line"] for row in line_intervals if row["start"] <= t < row["end"]), None)

    events = [
        {
            "kind": "peak perturbation",
            "time": round((peak - before) * DT, 6),
            "line": line_at((peak - before) * DT),
            "delta_hz_per_neuron": float(delta[peak]),
        }
    ]
    # Require a state to persist three frames (60 ms) before recording a transition.
    states = np.where(delta > threshold, 1, np.where(delta < -threshold, -1, 0))
    previous = 0
    for i in range(before, len(states) - 2):
        state = int(states[i])
        if state != previous and np.all(states[i : i + 3] == state):
            events.append(
                {
                    "kind": "activity transition",
                    "time": round((i - before) * DT, 6),
                    "line": line_at((i - before) * DT),
                    "state": {
                        -1: "below baseline band",
                        0: "within baseline band",
                        1: "above baseline band",
                    }[state],
                    "delta_hz_per_neuron": float(delta[i]),
                }
            )
            previous = state
    recovery = None
    tail_delta = delta[tail]
    stable_steps = round(0.2 / DT)
    for i in range(len(tail_delta) - stable_steps + 1):
        if np.all(np.abs(tail_delta[i : i + stable_steps]) <= threshold):
            recovery = i * DT
            break
    timeline = []
    for i in range(len(rates)):
        relative = i - before
        frame = frames[relative] if 0 <= relative < len(frames) else None
        timeline.append(
            {
                "time": round(relative * DT, 6),
                "phase": str(phase[i]),
                "spike_count": int(record["counts"][i]),
                "hz_per_neuron": float(rates[i]),
                "smoothed_hz_per_neuron": float(filtered[i]),
                "delta_hz_per_neuron": float(delta[i]),
                "rms": frame["rms"] if frame else 0,
                "injected_voltage": frame["injected_voltage"] if frame else 0,
                "line": line_at(relative * DT),
                "groups": {
                    name: (float(record["group_counts"][i, j] / (size * DT)) if size else None)
                    for j, (name, size) in enumerate(
                        zip(record["group_names"], record["group_sizes"])
                    )
                },
            }
        )
    response = {
        "units": "spikes per second per neuron (Hz/neuron), unless stated otherwise",
        "baseline": {
            "hz_per_neuron": base,
            "smoothed_sd": base_sd,
            "duration": BASELINE_SECONDS,
            "excluded_warmup": True,
        },
        "global": {
            "during_hz_per_neuron": float(rates[audio].mean()),
            "deviation_hz_per_neuron": float(rates[audio].mean() - base),
            "peak_perturbation_hz_per_neuron": float(delta[peak]),
            "peak_time": round((peak - before) * DT, 6),
            "tail_hz_per_neuron": float(rates[tail].mean()),
            "tail_deviation_hz_per_neuron": float(rates[tail].mean() - base),
            "recovery_seconds_after_audio_window": recovery,
            "recovery_censored": recovery is None,
            "tail_observed_seconds": TAIL_SECONDS,
            "audio_window_seconds": len(frames) * DT,
        },
        "populations": by_change,
        "strongest_activity": by_activity,
        "monitored_populations": monitored,
        "events": sorted(events, key=lambda e: e["time"]),
        "measurement_rules": {
            "global_smoothing_seconds": 0.1,
            "smoothing": "causal five-frame moving mean",
            "transition_band_hz_per_neuron": threshold,
            "transition_rule": "outside max(3 baseline smoothed SD, 0.02 Hz/neuron) for 60 ms",
            "recovery_rule": "first 200 ms continuously within that band; null = not observed in tail",
            "population_rank": "absolute audio-minus-baseline mean Hz per neuron; no minimum group size",
            "warning": "Descriptive single-run changes, not statistical significance or behavioral observations.",
        },
    }
    # Retain the changing types' actual 100 ms trajectories, separate from 20 ms global trace.
    selected = {p["name"] for p in by_change[:8]}
    population_timeline = []
    for j, name in enumerate(record["type_names"]):
        if str(name) not in selected:
            continue
        values = record["type_counts"][:, j]
        population_timeline.append(
            {
                "name": str(name),
                "points": [
                    {
                        "time": round((k * 5 - before) * DT, 6),
                        "hz_per_neuron": float(
                            count / (int(record["type_sizes"][j]) * min(5, len(rates) - k * 5) * DT)
                        ),
                    }
                    for k, count in enumerate(values)
                ],
            }
        )
    rank = {p["name"]: i for i, p in enumerate(by_change)}
    population_timeline.sort(key=lambda p: rank[p["name"]])
    return response, timeline, populations, population_timeline

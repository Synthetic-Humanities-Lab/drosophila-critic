"""Matched counterfactual: identical clock, reset, weights and random stream; zero input."""

import numpy as np

from .config import DT
from .response import smooth


def compare(poem, silence, lines):
    for key in ("phase", "type_names", "type_sizes", "group_names", "group_sizes"):
        if not np.array_equal(poem[key], silence[key]):
            raise ValueError(f"Mismatched control {key}")
    for key in ("seed", "runtime_weights_sha256", "configuration", "neurons"):
        if poem["fly"][key] != silence["fly"][key]:
            raise ValueError(f"Mismatched control {key}")
    before = poem["before"]
    if not np.array_equal(poem["counts"][:before], silence["counts"][:before]):
        raise ValueError("Pre-stimulus trajectories differ; control is not matched")
    audio = poem["phase"] == "audio"
    tail = poem["phase"] == "tail"
    n = poem["fly"]["neurons"]
    p = poem["counts"].astype(float) / (n * DT)
    s = silence["counts"].astype(float) / (n * DT)
    delta = smooth(p - s)
    filtered_silence = smooth(s)
    peak = before + int(np.argmax(np.abs(delta[audio])))
    time = (peak - before) * DT
    populations = []
    for j, name in enumerate(poem["type_names"]):
        if not str(name).strip():
            continue
        size = int(poem["type_sizes"][j])
        pr = float(poem["phase_type_counts"][1, j] / (size * audio.sum() * DT))
        sr = float(silence["phase_type_counts"][1, j] / (size * audio.sum() * DT))
        populations.append(
            dict(
                name=str(name),
                neurons=size,
                audio_hz_per_neuron=pr,
                silence_hz_per_neuron=sr,
                delta_hz_per_neuron=pr - sr,
            )
        )
    populations.sort(key=lambda r: (-abs(r["delta_hz_per_neuron"]), r["name"]))
    groups = []
    for j, name in enumerate(poem["group_names"]):
        size = poem["group_sizes"][j]
        if not size:
            groups.append(dict(name=name, neurons=0, available=False))
            continue
        pr = float(poem["group_counts"][audio, j].mean() / (size * DT))
        sr = float(silence["group_counts"][audio, j].mean() / (size * DT))
        groups.append(
            dict(
                name=name,
                neurons=size,
                available=True,
                audio_hz_per_neuron=pr,
                silence_hz_per_neuron=sr,
                delta_hz_per_neuron=pr - sr,
            )
        )
    return {
        "kind": "matched silence",
        "pairs": 1,
        "seed": poem["fly"]["seed"],
        "pre_stimulus_identical": True,
        "control_fly": silence["fly"],
        "duration": float(audio.sum() * DT),
        "global": {
            "poem_hz_per_neuron": float(p[audio].mean()),
            "silence_hz_per_neuron": float(s[audio].mean()),
            "delta_hz_per_neuron": float((p - s)[audio].mean()),
            "peak_delta_hz_per_neuron": float(delta[peak]),
            "peak_time": round(time, 6),
            "peak_line": next((r["line"] for r in lines if r["start"] <= time < r["end"]), None),
            "tail_delta_hz_per_neuron": float((p - s)[tail].mean()),
        },
        "populations": populations[:20],
        "monitored_populations": groups,
        "timeline": [
            {
                "time": round((i - before) * DT, 6),
                "silence_hz_per_neuron": float(filtered_silence[i]),
                "delta_hz_per_neuron": float(delta[i]),
            }
            for i in range(len(p))
        ],
        "rules": {
            "control": "Same seed, reset, duration and parameters; every auditory injection is zero.",
            "smoothing": "Causal 100 ms mean for traces and peak; unsmoothed phase means for rates.",
            "ranking": "Absolute poem minus matched silence mean Hz/neuron; includes small populations.",
            "limitation": "One paired seed. A model counterfactual, not a population norm, significance test or evidence of language processing.",
        },
    }

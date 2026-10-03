"""Adapt saved full-connectome runs for the shared encounter; never rerun or alter them."""

import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
GROUP_LABELS = {
    "global": ("Whole nervous system", "All simulated neurons."),
    "JO-A/B input": ("Hearing input", "The 138 cells receiving the sound-derived input."),
    "direct JON postsynaptic partners": (
        "Connected to hearing",
        "Cells connected directly to the hearing inputs. These are not injected with sound.",
    ),
    "descending_neuron": (
        "Brain → nerve cord",
        "Cells carrying signals from the brain toward the nerve cord. Firing is not movement.",
    ),
    "wing motor (flytalk WING_MN)": (
        "Wing motor cells",
        "The wing motor group identified by fly.ai. This is neural activity, not wing motion.",
    ),
}


def aggregate(counts, sizes, bin_steps=5, dt=0.02):
    """Rates retain the real duration of the last, potentially incomplete bin."""
    return np.asarray(
        [
            counts[i : i + bin_steps].sum(axis=0) / (min(bin_steps, len(counts) - i) * dt) / sizes
            for i in range(0, len(counts), bin_steps)
        ]
    )


def band(values):
    values = np.asarray(values)
    return {
        "mean": values.mean(axis=0).tolist(),
        "minimum": values.min(axis=0).tolist(),
        "maximum": values.max(axis=0).tolist(),
    }


def spatial_silence(template, source):
    lookup = np.full(166700, -1, np.int32)
    lookup[template["neuron_indices"]] = np.arange(template["displayed_neurons"])
    with np.load(source) as a:
        indices, offsets = a["neuron_indices"], a["offsets"]
        bins = []
        for i in range(0, len(offsets) - 1, 5):
            mapped = lookup[indices[int(offsets[i]) : int(offsets[min(i + 5, len(offsets) - 1)])]]
            bins.append(np.unique(mapped[mapped >= 0]).tolist())
    return {**template, "condition": "silence", "firing_bins": bins}


def save(path, value):
    path.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n")


def main():
    old = ROOT / "experiments/encounter-v1"
    target = ROOT / "experiments/encounter-v2"
    target.mkdir(exist_ok=True)
    manifest = json.loads((old / "manifest.json").read_text())
    result = json.loads((old / "result.json").read_text())
    encoding = json.loads((old / "encoding.json").read_text())
    model = json.loads((ROOT / "static/browser-model-v1/manifest.json").read_text())
    names = list(GROUP_LABELS)
    sizes = np.array([model["neurons"], *[len(model["groups"][n]) for n in names[1:]]])
    scales = np.zeros(len(names))
    input_scales = {"waveform_rms": 0.0, "displacement_nm": 0.0, "injection": 0.8}
    for key, performance in manifest["performances"].items():
        rates, raw = {}, {}
        for condition in ("sound", "silence"):
            raw[condition] = []
            for seed in result["seeds"]:
                suffix = "-g1" if condition == "sound" else ""
                path = (
                    ROOT / f"results/encounter-v1/{key}-{condition}-{seed}{suffix}/populations.npz"
                )
                with np.load(path) as a:
                    indices = [list(a["group_names"]).index(n) for n in names[1:]]
                    counts = np.column_stack((a["global_counts"], a["group_counts"][:, indices]))
                raw[condition].append(counts / sizes / 0.02)
            rates[condition] = np.array(
                [aggregate(r * sizes * 0.02, sizes) for r in raw[condition]]
            )
        rates["change"] = rates["sound"] - rates["silence"]
        frames = encoding["frames"][key]
        sound_frames = encoding["metadata"][key]["sound_frames"]
        summary = []
        for i, name in enumerate(names):
            summary.append(
                {
                    "id": name,
                    "sound": band([r[75 : 75 + sound_frames, i].mean() for r in raw["sound"]]),
                    "silence": band([r[75 : 75 + sound_frames, i].mean() for r in raw["silence"]]),
                    "change": band(
                        [
                            (a - b)[75 : 75 + sound_frames, i].mean()
                            for a, b in zip(raw["sound"], raw["silence"])
                        ]
                    ),
                    "after_change": band(
                        [
                            (a - b)[75 + sound_frames :, i].mean()
                            for a, b in zip(raw["sound"], raw["silence"])
                        ]
                    ),
                }
            )
        scales = np.maximum(
            scales, np.maximum(rates["sound"].max(axis=(0, 1)), rates["silence"].max(axis=(0, 1)))
        )
        rate, pcm = wavfile.read(old / performance["audio"])
        x = pcm.astype(np.float64) / 32768
        waveform = [
            float(np.sqrt(np.sum(x[i : i + 960] ** 2) / 960)) for i in range(0, len(x), 960)
        ]
        payload = {
            "schema_version": "fly-playback-v2",
            "id": key,
            "audio_duration": performance["duration"],
            "playback_duration": len(raw["sound"][0]) * 0.02 - 1.5,
            "start_time": -1.5,
            "bin_seconds": 0.1,
            "seeds": result["seeds"],
            "activity": {k: band(v) for k, v in rates.items()},
            "summary": summary,
            "input": {
                "frame_seconds": 0.02,
                "waveform_rms": waveform,
                "injection": [f["injected_voltage"] for f in frames],
                "displacement_nm": [
                    f["rms"] * encoding["metadata"][key]["reference_response"] / 0.1 for f in frames
                ],
            },
            "normalization": result["audio"][key]["normalization"],
            "source": "../encounter-v1/result.json",
            "body": {"available": False, "reason": "No qualified neural-to-body coupling"},
        }
        for field in ("waveform_rms", "displacement_nm"):
            input_scales[field] = max(input_scales[field], max(payload["input"][field]) * 1.05)
        save(target / f"playback-{key}.json", payload)
        spatial = json.loads((old / performance["spatial"]).read_text())
        silence = spatial_silence(
            spatial, ROOT / f"results/encounter-v1/{key}-silence-1101/spikes.npz"
        )
        save(target / f"silence-{key}.json", silence)
        performance.update(
            audio=f"../encounter-v1/{performance['audio']}",
            spatial=f"../encounter-v1/{performance['spatial']}",
            silence_spatial=f"silence-{key}.json",
            playback=f"playback-{key}.json",
        )
    manifest.update(
        schema_version="encounter-manifest-v2",
        input_scales=input_scales,
        groups=[
            {
                "id": n,
                "label": GROUP_LABELS[n][0],
                "description": GROUP_LABELS[n][1],
                "size": int(sizes[i]),
                "scale_max": float(scales[i]),
            }
            for i, n in enumerate(names)
        ],
        source="../encounter-v1/manifest.json",
        result="../encounter-v1/result.json",
        encoding="../encounter-v1/encoding.json",
        sensitivity="../encounter-v1/sensitivity.json",
    )
    save(target / "manifest.json", manifest)
    save(target / "display-neurons.json", {k: v for k, v in spatial.items() if k != "firing_bins"})
    print(f"Exported playback and actual silence samples: {target}")


if __name__ == "__main__":
    main()

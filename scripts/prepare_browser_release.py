"""Prepare an explicit browser-only model package after numerical/performance qualification."""

import json
import shutil

import numpy as np

from critic.config import ROOT
from critic.pipeline import save_json
from critic.receiver.healthy import SoundTransfer


def main():
    source = ROOT / "results/browser-benchmark"
    target = ROOT / "static/browser-model-v1"
    target.mkdir(exist_ok=True)
    manifest = json.loads((source / "manifest.json").read_text())
    manifest.pop("fixture")
    manifest["version"] = "lossless-pcg64-browser-v1"
    for array in manifest["arrays"].values():
        for part in array["parts"]:
            shutil.copy2(source / part["file"], target / part["file"])
    model = SoundTransfer()
    reference = abs(model.velocity_transfer(200)) * 0.5e6 / (2 * np.pi * 200)
    manifest["receiver"] = dict(
        transition=model.transition.tolist(),
        forcing=model.forcing.tolist(),
        reference_nm=reference,
        sample_rate=48000,
        frame_samples=960,
        air_velocity_gain=5e6,
        cap=0.8,
        decay_frames=5,
    )
    spatial = json.loads((ROOT / "experiments/encounter-v1/spatial-a.json").read_text())
    manifest["display_neurons"] = spatial["neuron_indices"]
    save_json(target / "manifest.json", manifest)
    # Deterministic acoustic fixture for the JS physical receiver.
    from critic.receiver.provisional import encode_provisional

    t = np.arange(48000) / 48000
    x = 0.07 * np.sin(2 * np.pi * 200 * t) * (t < 0.5)
    frames, _ = encode_provisional(x, 48000, "displacement", 1)
    save_json(
        ROOT / "tests/receiver-browser-fixture.json",
        {
            "waveform": "0.07*sin(2*pi*200*t), t<0.5; 48000 Hz, 1 s",
            "drive": [f["injected_voltage"] for f in frames],
        },
    )
    print(target)


if __name__ == "__main__":
    main()

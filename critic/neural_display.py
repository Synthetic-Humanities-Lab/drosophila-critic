"""Export measured spikes at supplied connectome coordinates; no invented wiring."""

import numpy as np


def export_neural_display(runner, directory):
    positions = runner.brain.positions
    if positions is None:
        return {"available": False, "reason": "No coordinates in upstream data"}
    valid = np.flatnonzero(np.isfinite(positions).all(axis=1))
    # Uniform deterministic index subsample, independent of firing or text.
    chosen = valid[np.linspace(0, len(valid) - 1, min(12000, len(valid)), dtype=int)]
    lookup = np.full(runner.brain.n, -1, dtype=np.int32)
    lookup[chosen] = np.arange(len(chosen))
    with np.load(directory / "spikes.npz") as spikes:
        indices, offsets = spikes["neuron_indices"], spikes["offsets"]
        bins = []
        for start in range(0, len(offsets) - 1, 5):
            fired = indices[int(offsets[start]) : int(offsets[min(start + 5, len(offsets) - 1)])]
            mapped = lookup[fired]
            bins.append(np.unique(mapped[mapped >= 0]).tolist())
        before = int(spikes["audio_start_step"])
    return {
        "available": True,
        "source": "MaleCNS brain.npz positions",
        "mapped_neurons": len(valid),
        "displayed_neurons": len(chosen),
        "selection": "12000 uniformly spaced valid neuron indices, independent of activity",
        "neuron_indices": chosen.tolist(),
        "positions": positions[chosen].tolist(),
        "start_time": -before * runner.brain.dt,
        "bin_seconds": 0.1,
        "firing_bins": bins,
        "meaning": "A point lights if this neuron spiked in the recorded 100 ms bin. Coordinates as supplied, not a reconstructed morphology.",
    }

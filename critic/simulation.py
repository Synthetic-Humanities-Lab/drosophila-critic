"""Adapter around the unmodified upstream FlyBrain, not a replacement model."""

import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

import numba
import numpy as np

from .config import (
    BASELINE_SECONDS,
    DATA,
    DT,
    SEED,
    TAIL_SECONDS,
    THREADS,
    UPSTREAM,
    UPSTREAM_COMMIT,
    WARMUP_SECONDS,
)

sys.path.insert(0, str(UPSTREAM))
from flybrain import FlyBrain  # noqa: E402
from flybrain.data import FILES  # noqa: E402
from flytalk import WING_MN, ear_cells  # noqa: E402


def sha256(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class SimulationRunner:
    """Owns one reusable brain; callers must serialize runs."""

    def __init__(self):
        numba.set_num_threads(THREADS)
        self.brain = FlyBrain(
            data=DATA, device="cpu", dt=DT, sensory_input=True, refractory=0.0, seed=SEED
        )
        self.data_hashes = {name: sha256(DATA / name) for name in FILES}
        if self.data_hashes != FILES:
            raise RuntimeError("Connectome file checksum differs from upstream brain-v1")
        b = self.brain
        self.ear = ear_cells(b)
        if len(self.ear) == 0:
            raise RuntimeError("No upstream JO-A/B neurons resolved; refusing a substitute")
        self.type_names, self.type_index, self.type_sizes = np.unique(
            b.cell_type, return_inverse=True, return_counts=True
        )
        # CSC columns are presynaptic: direct postsynaptic partners of JO-A/B.
        targets = np.unique(
            np.concatenate([b.indices[b.indptr[i] : b.indptr[i + 1]] for i in self.ear])
        )
        self.groups = {
            "JO-A/B input": self.ear,
            "direct JON postsynaptic partners": np.setdiff1d(targets, self.ear),
            "descending_neuron": b.cells(["descending_neuron"]),
            "wing motor (flytalk WING_MN)": b.cells(WING_MN),
        }
        for name in ("DNa02", "DNp01", "DNg100", "MDN", "pIP10", "dPR1"):
            self.groups[name] = b.cells([name])
        self.group_masks = {name: np.isin(np.arange(b.n), idx) for name, idx in self.groups.items()}
        self.source_hashes = {
            name: sha256(UPSTREAM / name)
            for name in (
                "flybrain/brain.py",
                "flybrain/build.py",
                "flybrain/reservoir.py",
                "flytalk.py",
            )
        }

    def inventory(self):
        b = self.brain
        with np.load(DATA / "brain.npz", allow_pickle=False) as meta:
            ids = meta["ids"]
        return {
            "upstream_commit": UPSTREAM_COMMIT,
            "data_sha256": self.data_hashes,
            "neurons": b.n,
            "connections": len(b.weights),
            "jon_total": len(self.ear),
            "jon_types": {
                str(t): int(np.sum(b.cell_type[self.ear] == t))
                for t in np.unique(b.cell_type[self.ear])
            },
            "jon_body_ids": ids[self.ear].astype(str).tolist(),
            "groups": {
                name: {"count": len(idx), "cell_types": sorted(set(map(str, b.cell_type[idx])))}
                for name, idx in self.groups.items()
            },
            "existing_upstream_groups": {
                name: {"count": len(idx), "cell_types": sorted(set(map(str, b.cell_type[idx])))}
                for name, idx in b.groups.items()
            },
            "warning": "Upstream punch/kick groups are arbitrary game mappings, not biological categories; not used.",
        }

    def run(self, frames: list[dict], directory: Path, progress=lambda *_: None, seed=SEED):
        if not frames:
            raise ValueError("At least one acoustic frame is required")
        numba.set_num_threads(THREADS)
        b = self.brain
        b.reset(seed)
        warmup, baseline, tail = [
            round(s / DT) for s in (WARMUP_SECONDS, BASELINE_SECONDS, TAIL_SECONDS)
        ]
        before = warmup + baseline
        steps = before + len(frames) + tail
        phase = np.array(
            ["warmup"] * warmup
            + ["baseline"] * baseline
            + ["audio"] * len(frames)
            + ["tail"] * tail
        )
        global_counts = np.zeros(steps, dtype=np.uint32)
        group_names = list(self.groups)
        group_counts = np.zeros((steps, len(group_names)), dtype=np.uint32)
        # All annotated populations: five-step bins retain 100 ms temporal evidence.
        bin_steps = 5
        type_counts = np.zeros(
            ((steps + bin_steps - 1) // bin_steps, len(self.type_names)), dtype=np.uint32
        )
        phase_type_counts = np.zeros((3, len(self.type_names)), dtype=np.uint64)
        spikes, offsets = [], [0]
        weights_before = hashlib.sha256(b.weights.tobytes()).hexdigest()
        for step in range(steps):
            audio_step = step - before
            amount = (
                frames[audio_step]["injected_voltage"] if 0 <= audio_step < len(frames) else 0.0
            )
            fired = b.step(inject=[(self.ear, amount)])
            global_counts[step] = len(fired)
            group_counts[step] = [
                np.count_nonzero(self.group_masks[name][fired]) for name in group_names
            ]
            counts = np.bincount(self.type_index[fired], minlength=len(self.type_names)).astype(
                np.uint32
            )
            type_counts[step // bin_steps] += counts
            p = {"baseline": 0, "audio": 1, "tail": 2}.get(phase[step])
            if p is not None:
                phase_type_counts[p] += counts
            spikes.append(fired.astype(np.uint32))
            offsets.append(offsets[-1] + len(fired))
            if step % 25 == 0 or step == steps - 1:
                progress("READING", (step + 1) / steps)
        weights_after = hashlib.sha256(b.weights.tobytes()).hexdigest()
        if weights_before != weights_after:
            raise RuntimeError("Connectome weights changed during simulation")
        np.savez_compressed(
            directory / "spikes.npz",
            neuron_indices=np.concatenate(spikes),
            offsets=np.array(offsets, np.uint64),
            dt=DT,
            audio_start_step=before,
            index_reference="data/brain.npz ids",
        )
        np.savez_compressed(
            directory / "populations.npz",
            type_names=self.type_names,
            type_sizes=self.type_sizes,
            bin_counts=type_counts,
            phase_counts=phase_type_counts,
            bin_steps=bin_steps,
            dt=DT,
            group_names=group_names,
            group_counts=group_counts,
            global_counts=global_counts,
            phase=phase,
        )
        configuration = {
            name: float(getattr(b, name))
            for name in (
                "tau",
                "gain",
                "tonic",
                "noise_hz",
                "noise_amp",
                "decay",
                "refractory_steps",
            )
        }
        configuration.update(
            {
                "sensory_input": True,
                "device": "cpu",
                "batch": 1,
                "numba_threads": THREADS,
                "warmup_seconds": WARMUP_SECONDS,
                "baseline_seconds": BASELINE_SECONDS,
                "tail_seconds": TAIL_SECONDS,
            }
        )
        provenance = {
            "connectome": "MaleCNS v1.0",
            "simulator": "flybrain.FlyBrain",
            "version": "0.1.0",
            "upstream_commit": UPSTREAM_COMMIT,
            "source_sha256": self.source_hashes,
            "data_sha256": self.data_hashes,
            "weights_unchanged": True,
            "runtime_weights_sha256": weights_after,
            "neurons": b.n,
            "connections": len(b.weights),
            "timestep": DT,
            "configuration": configuration,
            "seed": seed,
            "rng": type(b.rng.bit_generator).__name__,
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                **{p: importlib.metadata.version(p) for p in ("numpy", "numba", "scipy")},
            },
            "input_neurons": len(self.ear),
            "input_types": sorted(set(map(str, b.cell_type[self.ear]))),
        }
        return {
            "counts": global_counts,
            "group_counts": group_counts,
            "group_names": group_names,
            "group_sizes": [len(self.groups[n]) for n in group_names],
            "type_names": self.type_names,
            "type_sizes": self.type_sizes,
            "phase_type_counts": phase_type_counts,
            "type_counts": type_counts,
            "phase": phase,
            "before": before,
            "fly": provenance,
        }


if __name__ == "__main__":
    runner = SimulationRunner()
    target = Path(__file__).resolve().parent.parent / "docs" / "population-inventory.json"
    target.write_text(json.dumps(runner.inventory(), indent=2))
    print(target)

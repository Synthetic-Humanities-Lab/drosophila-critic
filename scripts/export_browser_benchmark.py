"""Lossless full-connectome export and original-Python numerical fixtures."""

import gzip
import hashlib
import json

import numpy as np

from critic.config import DT, ROOT
from critic.pipeline import save_json
from critic.simulation import SimulationRunner

OUT = ROOT / "results/browser-benchmark"


def write_array(name, array):
    raw = array.tobytes()
    parts = []
    for index, start in enumerate(range(0, len(raw), 24 * 1024 * 1024)):
        block = raw[start : start + 24 * 1024 * 1024]
        compressed = gzip.compress(block, compresslevel=6, mtime=0)
        filename = f"{name}-{index}.bin"
        (OUT / filename).write_bytes(compressed)
        parts.append(
            dict(
                file=filename,
                sha256=hashlib.sha256(compressed).hexdigest(),
                bytes=len(compressed),
                raw_bytes=len(block),
            )
        )
    return dict(
        dtype=str(array.dtype),
        length=array.size,
        sha256=hashlib.sha256(raw).hexdigest(),
        parts=parts,
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    runner = SimulationRunner()
    b = runner.brain
    arrays = {
        name: write_array(name, array)
        for name, array in (
            ("indptr", b.indptr.astype("<u4")),
            ("indices", b.indices.astype("<u4")),
            ("weights", b.weights.astype("<f4")),
        )
    }
    manifest = dict(
        version="lossless-browser-benchmark-v1",
        neurons=b.n,
        connections=len(b.weights),
        arrays=arrays,
        ear=runner.ear.tolist(),
        groups={k: v.tolist() for k, v in runner.groups.items()},
        configuration=dict(
            dt=DT,
            decay=float(b.decay),
            gain=b.gain,
            tonic=float(b.tonic),
            noise_probability=b.noise_hz * DT,
            noise_amplitude=b.noise_amp,
            threads=4,
        ),
        upstream_commit=runner.inventory()["upstream_commit"],
        weight_quantization=False,
        random_states={
            str(seed): {
                k: str(v)
                for k, v in np.random.default_rng(seed).bit_generator.state["state"].items()
            }
            for seed in (1101, 1102, 1103, 1104)
        },
    )
    # Supply exactly the NumPy noise realizations consumed by original FlyBrain.
    seed = 1101
    random = np.random.default_rng(seed)
    b.reset(seed)
    noise, offsets, expected = [], [0], []
    for step in range(100):
        idx = np.flatnonzero(random.random((b.n, 1)) < b.noise_hz * DT).astype("<u4")
        noise.append(idx)
        offsets.append(offsets[-1] + len(idx))
        amount = 0.3 if 25 <= step < 75 else 0.0
        fired = b.step(inject=[(runner.ear, amount)])
        expected.append(
            dict(
                input=amount,
                voltage_sha256=hashlib.sha256(b.v.tobytes()).hexdigest(),
                spikes_sha256=hashlib.sha256(fired.astype("<u4").tobytes()).hexdigest(),
                count=len(fired),
                group_counts={
                    k: int(np.count_nonzero(mask[fired])) for k, mask in runner.group_masks.items()
                },
            )
        )
    manifest["fixture"] = dict(
        seed=seed,
        noise=write_array("noise", np.concatenate(noise)),
        offsets=offsets,
        expected=expected,
    )
    manifest["transfer_bytes"] = sum(p["bytes"] for a in arrays.values() for p in a["parts"])
    manifest["connectivity_memory_bytes"] = sum(a["length"] * 4 for a in arrays.values())
    save_json(OUT / "manifest.json", manifest)
    print(
        json.dumps(
            {
                k: manifest[k]
                for k in ("transfer_bytes", "connectivity_memory_bytes", "neurons", "connections")
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

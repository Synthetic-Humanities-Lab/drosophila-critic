"""Inspect named motor-related outputs in saved poem/silence pairs; infer no motion."""

import json
from pathlib import Path

import numpy as np

from critic.config import DATA

ROOT = Path(__file__).resolve().parents[1]


def rates(path, groups):
    with np.load(path) as data:
        spikes, offsets = data["neuron_indices"], data["offsets"]
        counts = []
        for cells in groups.values():
            events = np.flatnonzero(np.isin(spikes, cells))
            steps = np.searchsorted(offsets, events, side="right") - 1
            counts.append(np.bincount(steps, minlength=len(offsets) - 1) / len(cells) / 0.02)
        return np.asarray(counts)


def main():
    with np.load(DATA / "brain.npz") as metadata:
        types, sides = metadata["cell_type"], metadata["side"]
        groups = {}
        for name, side in [
            ("DNa02", "left"),
            ("DNa02", "right"),
            ("MDN", None),
            ("DNg100", None),
            ("DNp01", None),
        ]:
            mask = types == name
            if side:
                mask &= sides == {"left": "L", "right": "R"}[side]
            cells = np.flatnonzero(mask)
            if not len(cells):
                raise ValueError(f"No cells for {name} {side}; check actual annotations")
            groups[f"{name} {side or 'both'}"] = cells
        identities = {k: metadata["ids"][v].astype(str).tolist() for k, v in groups.items()}
    encoding = json.loads((ROOT / "experiments/encounter-v1/encoding.json").read_text())
    report = {
        "schema_version": "body-output-audit-v1",
        "groups_body_ids": identities,
        "units": "spikes per second per cell",
        "runs": [],
        "inference": "No conversion to body speed or turning angle is qualified by these counts.",
    }
    for reader in ("a", "b"):
        count = encoding["metadata"][reader]["sound_frames"]
        for seed in (1101, 1102, 1103, 1104):
            print(reader, seed, flush=True)
            sound = rates(
                ROOT / f"results/encounter-v1/{reader}-sound-{seed}-g1/spikes.npz", groups
            )
            silence = rates(
                ROOT / f"results/encounter-v1/{reader}-silence-{seed}/spikes.npz", groups
            )
            delta = sound[:, 75 : 75 + count] - silence[:, 75 : 75 + count]
            report["runs"].append(
                {
                    "reader": reader,
                    "seed": seed,
                    "sound_mean": sound[:, 75 : 75 + count].mean(axis=1).tolist(),
                    "silence_mean": silence[:, 75 : 75 + count].mean(axis=1).tolist(),
                    "change_mean": delta.mean(axis=1).tolist(),
                    "changed_timesteps": np.count_nonzero(delta, axis=1).tolist(),
                    "DNa02_left_minus_right_change": float((delta[0] - delta[1]).mean()),
                }
            )
    target = ROOT / "experiments/body-controller-v1/poem-output-audit.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()

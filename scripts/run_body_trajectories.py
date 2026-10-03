"""Replay full selected-population spike counts through the fixed body adapter."""

import argparse
import gzip
import hashlib
import json
import os
import time
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "disable")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/drosophila-mpl")


def run(rates, output, *, metadata, sound_seconds=0, baseline=1.5):
    import numpy as np

    from critic.body_adapter import NeuralBodyAdapter
    from critic.body_runtime import BodyRuntime
    from critic.body_supervisor import BodySupervisor

    body, adapter, supervisor = BodyRuntime(), NeuralBodyAdapter(), BodySupervisor()
    frames, commands, failures = [], [], []
    start = time.perf_counter()
    inverted_for = 0.0
    inverted_total = 0.0
    for frame, row in enumerate(rates):
        command = adapter.step(row)
        recorded_command = command.copy()
        boundary = False
        until = (frame + 1) * 0.02
        while body.data.time < until - 1e-8:
            yaw = float(np.arctan2(body.data.xmat[body.root, 3], body.data.xmat[body.root, 0]))
            applied = supervisor.command(
                command,
                time=float(body.data.time),
                dt=0.0002 if supervisor.state in ["takeoff", "flight", "landing"] else 0.002,
                position=body.data.xpos[body.root],
                yaw=yaw,
                landed=body.landed,
            )
            boundary |= applied["boundary"]
            body.step(**{k: applied[k] for k in ["state", "speed", "turn", "height"]})
            command["takeoff"] = False
        snapshot = body.snapshot()
        frames.append(snapshot)
        commands.append(
            {
                **recorded_command,
                **{k: applied[k] for k in ["state", "speed", "turn"]},
                "body_reference_speed": body.command_speed,
                "body_reference_turn": body.command_turn,
                "boundary": boundary,
            }
        )
        root = body.data.xpos[body.root]
        if abs(root[0]) > 10 or abs(root[1]) > 8 or root[2] > 10 or root[2] < 0:
            failures.append(f"Arena escape at {body.data.time:.3f}s: {root}")
        if body.data.xmat[body.root, 8] < 0:
            inverted_for += 0.02
            inverted_total += 0.02
        else:
            inverted_for = 0
        if inverted_for > 0.25:
            failures.append(f"Body remained inverted for over 250 ms at {body.data.time:.3f}s")
        if failures:
            break
        if frame % 500 == 0:
            print(output.name, frame, len(rates), supervisor.state, root.round(3), flush=True)
    positions = np.asarray([f["positions"] for f in frames], dtype=np.float32)
    quats = np.asarray([f["quaternions"] for f in frames], dtype=np.float32)
    xyz = positions[:, body.root]
    distance = np.linalg.norm(np.diff(xyz[:, :2], axis=0), axis=1)
    state = [f["state"] for f in frames]
    ground = np.array([not f["airborne"] for f in frames])
    after = np.arange(len(frames)) * 0.02 >= baseline + sound_seconds
    yaw = np.unwrap(
        np.arctan2(
            2
            * (
                quats[:, body.root, 0] * quats[:, body.root, 3]
                + quats[:, body.root, 1] * quats[:, body.root, 2]
            ),
            1 - 2 * (quats[:, body.root, 2] ** 2 + quats[:, body.root, 3] ** 2),
        )
    )
    metrics = {
        "distance_walked_cm": float(distance[ground[1:]].sum()),
        "flight_seconds": float(np.count_nonzero(~ground) * 0.02),
        "turns_revolutions": float(np.abs(np.diff(yaw)).sum() / (2 * np.pi)),
        "after_voice_distance_cm": float(distance[after[1:]].sum()),
        "boundary_seconds": sum(c["boundary"] for c in commands) * 0.02,
        "minimum_upright": min(float(1 - 2 * (q[1] ** 2 + q[2] ** 2)) for q in quats[:, body.root]),
        "wall_seconds": time.perf_counter() - start,
        "inverted_seconds": inverted_total,
        "failures": failures,
        "complete": not failures,
    }
    output.parent.mkdir(exist_ok=True, parents=True)
    result = {
        "schema_version": "fly-body-playback-v1",
        "time": [round(f["time"] - baseline, 6) for f in frames],
        "body_names": body.body_names,
        "positions": positions.tolist(),
        "quaternions": quats.tolist(),
        "states": state,
        "airborne": (~ground).tolist(),
        "commands": commands,
        "events": sorted(
            [
                {**e, "time": round(e["time"] - baseline, 6)}
                for e in supervisor.events + body.events
            ],
            key=lambda e: e["time"],
        ),
        "metrics": metrics,
        "provenance": metadata,
    }
    output.with_suffix(".json.gz").write_bytes(
        gzip.compress(json.dumps(result, separators=(",", ":")).encode(), mtime=0)
    )
    np.savez_compressed(
        output.with_suffix(".npz"),
        positions=positions,
        quaternions=quats,
        time=result["time"],
        states=state,
        body_names=body.body_names,
    )
    output.with_suffix(".json").write_text(
        json.dumps(
            {k: result[k] for k in ["schema_version", "provenance", "metrics", "events"]}, indent=2
        )
    )
    print(output.name, metrics, flush=True)
    if failures:
        raise RuntimeError("; ".join(failures))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostic", action="store_true")
    parser.add_argument("--reader", choices=["a", "b"], default="a")
    parser.add_argument("--condition", choices=["sound", "silence"], default="silence")
    parser.add_argument("--seed", type=int, default=1101)
    args = parser.parse_args()
    import numpy as np

    from critic.body_adapter import CONFIG, GROUPS, population_indices
    from scripts.audit_body_outputs import rates as extract_rates

    metadata = {
        "adapter": CONFIG,
        "body": json.loads(Path("results/body-controller/export/model.json").read_text()),
        "policy_parity": json.loads(
            Path("results/body-controller/export/policy-parity.json").read_text()
        ),
        "seed": args.seed,
        "feedback": "Body sensors feed only the body policies; sound field is imposed.",
    }
    metadata["implementation_sha256"] = {
        name: hashlib.sha256(Path("critic", name).read_bytes()).hexdigest()
        for name in ["body_adapter.py", "body_supervisor.py", "body_runtime.py", "body_policy.py"]
    }
    if args.diagnostic:
        rows = []
        for i in range(550):
            t = i * 0.02
            r = {k: 0.0 for k in GROUPS}
            if t < 2:
                r["motor_walk"] = 5
                r["motor_turn_left"] = 3 if t > 1 else 0
            if i == 105:
                r["motor_takeoff"] = 25
            if 2 < t < 5:
                r["motor_flight"] = 3
                r["motor_flight_left"] = 4
            if t > 8:
                r["motor_walk"] = 4
            rows.append(r)
        run(
            rows,
            Path("results/body-controller/combined/arena-proof"),
            metadata={**metadata, "input": "Controlled population rates, not a poem"},
            baseline=0,
        )
        return
    with np.load("data/brain.npz") as brain:
        groups = population_indices(brain)
        metadata["population_ids"] = {
            k: brain["ids"][v].astype(str).tolist() for k, v in groups.items()
        }
    suffix = "-g1" if args.condition == "sound" else ""
    name = f"{args.reader}-{args.condition}-{args.seed}"
    path = Path(f"results/encounter-v1/{name}{suffix}/spikes.npz")
    counts = extract_rates(path, groups)
    rows = [dict(zip(groups, row)) for row in counts.T]
    encoding = json.loads(Path("experiments/encounter-v1/encoding.json").read_text())
    metadata.update(
        input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        reader=args.reader,
        condition=args.condition,
    )
    run(
        rows,
        Path(f"results/body-controller/trajectories/{name}"),
        metadata=metadata,
        sound_seconds=encoding["metadata"][args.reader]["sound_frames"] * 0.02,
    )


if __name__ == "__main__":
    main()

"""Exercise the combined body before connecting neural outputs."""

import argparse
import json
import os
import time
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "disable")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/drosophila-mpl")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["walk", "flight", "transition"], default="walk")
    parser.add_argument("--seconds", type=float, default=2)
    args = parser.parse_args()
    import mujoco
    import numpy as np

    from critic.body_runtime import BodyRuntime, orientation

    body = BodyRuntime()
    if args.mode == "flight":
        body.data.qpos[:3] = [0, 0, 2]
        body.data.qpos[3:7] = orientation(0, -np.deg2rad(47.5))
        body.data.qvel[0] = 30
        q, v = body.wpg.reset(return_qvel=True)
        body.data.qpos[body.wing_q] = q
        for j in body.views["walking"]["qpos"][19:]:
            body.data.qpos[j] = body.model.qpos_spring[j]
        for name, vel in zip(
            [
                "walker/wing_" + axis + "_" + side
                for side in ["left", "right"]
                for axis in ["yaw", "roll", "pitch"]
            ],
            v,
        ):
            body.data.qvel[body.model.jnt_dofadr[body.id("joint", name)]] = vel
        mujoco.mj_forward(body.model, body.data)
        body.flight_blend = 1
    frames = []
    start = time.perf_counter()
    next_frame = 0.0
    while body.data.time < args.seconds - 1e-8:
        t = body.data.time
        if args.mode == "walk":
            state, speed, turn = "walking", 2, 1 if t > 1 else 0
        elif args.mode == "flight":
            state, speed, turn = "flight", 30, 0
        elif t < 1:
            state, speed, turn = "walking", 2, 0
        elif t < 1.5:
            state, speed, turn = "takeoff", 8, 0
        elif t < 2.5:
            state, speed, turn = "flight", 15, 1
        elif t < 4.5:
            state, speed, turn = "landing", 1, 0
        else:
            state, speed, turn = "walking", 2, 0
        body.step(speed=speed, turn=turn, state=state)
        if body.data.time >= next_frame:
            frame = body.snapshot()
            frames.append(frame)
            next_frame += 0.01
            if len(frames) % 50 == 0:
                print(
                    round(body.data.time, 3),
                    state,
                    body.data.xpos[body.root].round(4),
                    "upright",
                    round(float(body.data.xmat[body.root, 8]), 3),
                    flush=True,
                )
    out = Path("results/body-controller/combined")
    out.mkdir(exist_ok=True)
    np.savez_compressed(
        out / f"{args.mode}.npz",
        positions=[f["positions"] for f in frames],
        quaternions=[f["quaternions"] for f in frames],
        time=[f["time"] for f in frames],
        states=[f["state"] for f in frames],
        body_names=body.body_names,
    )
    report = {
        "mode": args.mode,
        "seconds": float(body.data.time),
        "wall_seconds": time.perf_counter() - start,
        "final_position": body.data.xpos[body.root].tolist(),
        "events": body.events,
        "minimum_height": min(float(f["positions"][body.root, 2]) for f in frames),
    }
    (out / f"{args.mode}.json").write_text(json.dumps(report, indent=2))
    print(report, flush=True)


if __name__ == "__main__":
    main()

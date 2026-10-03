"""Bounded command test of the published flybody walking policy; no neural coupling."""

import argparse
import faulthandler
import hashlib
import importlib.metadata
import json
import os
import platform
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.environ.setdefault("MUJOCO_GL", "disable")
    os.environ.setdefault("MPLBACKEND", "Agg")
    faulthandler.dump_traceback_later(300, exit=True)
    import numpy as np
    import tensorflow as tf
    import tensorflow_probability as tfp
    from flybody.fly_envs import walk_imitation
    from flybody.tasks.synthetic_trajectories import constant_speed_trajectory

    tf.config.threading.set_intra_op_parallelism_threads(1)
    tf.config.threading.set_inter_op_parallelism_threads(1)
    # The 2024 snapshot names these composite specs explicitly. Register them
    # with TFP's public compatibility decorator before decoding the snapshot.
    for name in ("Independent", "MultivariateNormalDiag", "Normal", "TransformedDistribution"):
        tfp.experimental.auto_composite_tensor(getattr(tfp.distributions, name))
    policy = tf.saved_model.load(str(args.policy))
    report = {
        "schema_version": "flybody-command-test-v1",
        "controller_commit": "d015e9bfe441bd90ae431bac24c55cb74bdbce26",
        "policy_sha256": hashlib.sha256((args.policy / "saved_model.pb").read_bytes()).hexdigest(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            **{
                p: importlib.metadata.version(p)
                for p in ("tensorflow", "tensorflow-probability", "dm-control", "mujoco", "numpy")
            },
        },
        "protocol": {
            "seed": 1101,
            "steps": 600,
            "dt": 0.002,
            "action": "mean of published action distribution, as upstream TestPolicyWrapper",
            "acceptance": "No early termination, finite state, and maximum tracking error below the upstream 0.3 cm termination distance. Repeat trajectory must be identical.",
            "limitation": "A controller command test. No brain output, sound, or poem supplies these trajectories. No browser controller qualification.",
        },
        "runs": [],
    }
    trajectories = []
    for name, speed, yaw in [
        ("stand", 0, 0),
        ("forward", 2, 0),
        ("turn", 2, 2),
        ("forward_repeat", 2, 0),
    ]:
        print(f"Testing {name}", flush=True)
        start = time.perf_counter()
        env = walk_imitation(random_state=np.random.RandomState(1101))
        qpos, qvel = constant_speed_trajectory(700, speed=speed, yaw_speed=yaw)
        env.task._traj_generator.set_next_trajectory(qpos, qvel)
        timestep = env.reset()
        positions, errors, actions = [], [], []
        for step in range(600):
            observation = {
                k: tf.convert_to_tensor(v[None, ...], dtype=tf.float32)
                for k, v in timestep.observation.items()
            }
            action = policy(observation).mean()[0].numpy()
            timestep = env.step(action)
            position, _ = env.task._walker.get_pose(env.physics)
            positions.append(np.asarray(position).copy())
            errors.append(float(np.linalg.norm(position - qpos[step + 1, :3])))
            actions.append(action.copy())
            if timestep.last():
                break
        positions = np.asarray(positions)
        trajectories.append(positions)
        report["runs"].append(
            {
                "name": name,
                "command_cm_per_second": speed,
                "command_yaw_radians_per_second": yaw,
                "steps": len(positions),
                "wall_seconds": time.perf_counter() - start,
                "end_position_cm": positions[-1].tolist(),
                "maximum_tracking_error_cm": max(errors),
                "mean_tracking_error_cm": float(np.mean(errors)),
                "finite": bool(np.isfinite(positions).all() and np.isfinite(actions).all()),
                "trajectory_sha256": hashlib.sha256(positions.tobytes()).hexdigest(),
                "passed": bool(
                    len(positions) == 600 and np.isfinite(positions).all() and max(errors) < 0.3
                ),
            }
        )
        env.close()
    report["repeat_exact"] = bool(np.array_equal(trajectories[1], trajectories[3]))
    report["passed"] = report["repeat_exact"] and all(r["passed"] for r in report["runs"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    faulthandler.cancel_dump_traceback_later()


if __name__ == "__main__":
    main()

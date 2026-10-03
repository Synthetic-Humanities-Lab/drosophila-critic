"""Reproduce the published flight policy with its original wingbeat pattern."""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "disable")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/drosophila-mpl")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=0.4)
    parser.add_argument("--output", type=Path, default=Path("results/body-controller/flight-test"))
    args = parser.parse_args()
    import numpy as np
    import tensorflow as tf
    import tensorflow_probability as tfp
    from flybody.fly_envs import flight_imitation
    from flybody.tasks.synthetic_trajectories import constant_speed_trajectory

    tf.config.threading.set_intra_op_parallelism_threads(1)
    tf.config.threading.set_inter_op_parallelism_threads(1)
    for name in ("Independent", "MultivariateNormalDiag", "Normal", "TransformedDistribution"):
        tfp.experimental.auto_composite_tensor(getattr(tfp.distributions, name))
    policy = tf.saved_model.load("results/body-controller/policies/flight")
    print("Policy variables", [(v.name, list(v.shape)) for v in policy._variables], flush=True)

    @tf.function
    def act(observation):
        return policy(observation).mean()[0]

    args.output.mkdir(parents=True, exist_ok=True)
    pattern = Path("results/body-controller/flight-data/wing_pattern_fmech.npy")
    report = {
        "source": "TuragaLab/flybody d015e9bfe441bd90ae431bac24c55cb74bdbce26",
        "wing_pattern_sha256": hashlib.sha256(pattern.read_bytes()).hexdigest(),
        "seed": 1101,
        "neural_coupling": False,
        "runs": [],
    }
    for name, speed, yaw in [("straight", 30, 0), ("turn", 30, 3), ("repeat", 30, 0)]:
        start = time.perf_counter()
        env = flight_imitation(
            wpg_pattern_path=str(pattern), random_state=np.random.RandomState(1101)
        )
        env._time_limit = args.seconds + 1
        env.task._time_limit = args.seconds + 1
        n = round(args.seconds / 0.0002)
        qpos, qvel = constant_speed_trajectory(
            n + 100,
            speed=speed,
            yaw_speed=yaw,
            init_pos=(0, 0, 2),
            body_rot_angle_y=-47.5,
            control_timestep=0.0002,
        )
        env.task._traj_generator.set_next_trajectory(qpos, qvel)
        ts = env.reset()
        observations = {k: list(v.shape) for k, v in ts.observation.items()}
        positions, rotations, states, errors = [], [], [], []
        for step in range(n):
            action = act(
                {
                    k: tf.convert_to_tensor(v[None], dtype=tf.float32)
                    for k, v in ts.observation.items()
                }
            ).numpy()
            ts = env.step(action)
            errors.append(
                float(np.linalg.norm(env.physics.data.subtree_com[1] - qpos[step + 1, :3]))
            )
            if step % 50 == 0:
                positions.append(env.physics.data.xpos.copy())
                rotations.append(env.physics.data.xquat.copy())
                states.append(env.physics.data.qpos.copy())
            if ts.last():
                break
        finite = bool(np.isfinite(states).all())
        np.savez_compressed(
            args.output / f"{name}.npz",
            positions=positions,
            rotations=rotations,
            qpos=states,
            dt=0.01,
            body_names=[
                env.physics.model.id2name(i, "body") or "world"
                for i in range(env.physics.model.nbody)
            ],
        )
        result = {
            "name": name,
            "steps": step + 1,
            "seconds": float(env.physics.data.time),
            "wall_seconds": time.perf_counter() - start,
            "finite": finite,
            "max_error_cm": max(errors),
            "final_position_cm": positions[-1][1].tolist(),
            "state_sha256": hashlib.sha256(np.asarray(states).tobytes()).hexdigest(),
            "passed": finite and step + 1 == n and max(errors) < 2,
            "observations": observations,
        }
        report["runs"].append(result)
        print(result, flush=True)
        env.close()
    report["repeat_exact"] = report["runs"][0]["state_sha256"] == report["runs"][2]["state_sha256"]
    report["passed"] = report["repeat_exact"] and all(x["passed"] for x in report["runs"])
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    if not report["passed"]:
        raise SystemExit("Flight controller qualification failed; inspect report.json")


if __name__ == "__main__":
    main()

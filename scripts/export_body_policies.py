"""Export and check mean-policy inference against the actual saved models."""

import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "disable")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/drosophila-mpl")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")


def main():
    import numpy as np
    import tensorflow as tf
    import tensorflow_probability as tfp
    from flybody.fly_envs import flight_imitation, walk_imitation

    from critic.body_policy import FrozenBodyPolicy

    tf.config.threading.set_intra_op_parallelism_threads(1)
    tf.config.threading.set_inter_op_parallelism_threads(1)
    for name in ("Independent", "MultivariateNormalDiag", "Normal", "TransformedDistribution"):
        tfp.experimental.auto_composite_tensor(getattr(tfp.distributions, name))
    out = Path("results/body-controller/export")
    out.mkdir(parents=True, exist_ok=True)
    reports = {}
    for kind, factory in [("walking", walk_imitation), ("flight", flight_imitation)]:
        kwargs = (
            {"wpg_pattern_path": "results/body-controller/flight-data/wing_pattern_fmech.npy"}
            if kind == "flight"
            else {}
        )
        env = factory(random_state=np.random.RandomState(1101), **kwargs)
        ts = env.reset()
        policy = tf.saved_model.load(f"results/body-controller/policies/{kind}")
        variables = [v.numpy() for v in policy._variables]
        keys = sorted(ts.observation)
        port = FrozenBodyPolicy(variables, keys)
        fixtures = []
        errors = []
        relative_errors = []
        applied_errors = []
        rng = np.random.default_rng(91)
        for i in range(20):
            observation = (
                ts.observation
                if i < 10
                else {
                    k: rng.normal(size=v.shape).astype(np.float32)
                    for k, v in ts.observation.items()
                }
            )
            expected = (
                policy(
                    {k: tf.convert_to_tensor(v[None], tf.float32) for k, v in observation.items()}
                )
                .mean()[0]
                .numpy()
            )
            actual = port(observation)
            error = float(np.max(np.abs(actual - expected)))
            errors.append(error)
            relative_errors.append(error / max(1.0, float(np.max(np.abs(expected)))))
            spec = env.action_spec()
            applied_errors.append(
                float(
                    np.max(
                        np.abs(
                            np.clip(actual, spec.minimum, spec.maximum)
                            - np.clip(expected, spec.minimum, spec.maximum)
                        )
                    )
                )
            )
            fixtures.append(
                {
                    "observation": {k: np.asarray(v).tolist() for k, v in observation.items()},
                    "expected": expected.tolist(),
                    "ctrlrange": np.stack([spec.minimum, spec.maximum], axis=1).tolist(),
                }
            )
            if i < 10:
                ts = env.step(expected)
        np.savez(
            out / f"{kind}.npz",
            n=len(variables),
            keys=keys,
            **{f"v{i}": a for i, a in enumerate(variables)},
        )
        (out / f"{kind}-fixtures.json").write_text(json.dumps(fixtures))
        # Names are the contract for observing a policy from a combined body.
        w = env.task._walker
        info = {
            "observations": {k: list(v.shape) for k, v in ts.observation.items()},
            "joints": [j.full_identifier for j in w.observable_joints],
            "actuators": [a.full_identifier for a in w.mjcf_model.find_all("actuator")],
            "action_names": env.action_spec().name.split("\t"),
            "appendages": [s.full_identifier for s in w.appendages],
            "root": w.root_body.full_identifier,
            "sensors": {
                s: [v.full_identifier for v in getattr(w.mjcf_model.sensor, s)]
                for s in ["force", "touch", "accelerometer", "gyro", "velocimeter"]
            },
        }
        (out / f"{kind}-observation.json").write_text(json.dumps(info, indent=2))
        reports[kind] = {
            "maximum_absolute_error": max(errors),
            "fixtures": len(fixtures),
            "maximum_relative_infinity_norm_error": max(relative_errors),
            "maximum_applied_action_error": max(applied_errors),
            "tolerance": "1e-5 relative infinity norm and 1e-4 absolute after the model's actuator limits; random out-of-domain observations can produce unbounded policy means",
            "passed": max(relative_errors) < 1e-5 and max(applied_errors) < 1e-4,
            "saved_model_sha256": hashlib.sha256(
                Path(f"results/body-controller/policies/{kind}/saved_model.pb").read_bytes()
            ).hexdigest(),
        }
        print(kind, reports[kind], flush=True)
        env.close()
    (out / "policy-parity.json").write_text(json.dumps(reports, indent=2))
    assert all(r["passed"] for r in reports.values()), reports


if __name__ == "__main__":
    main()

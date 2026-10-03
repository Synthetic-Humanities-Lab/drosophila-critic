"""Reference observations and physics steps for the official WASM port."""

import json
import os
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "disable")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/drosophila-mpl")


def main():
    import mujoco
    import numpy as np

    from critic.body_runtime import BodyRuntime

    b = BodyRuntime()
    fixtures = []

    def capture():
        state = {
            "qpos": b.data.qpos.tolist(),
            "qvel": b.data.qvel.tolist(),
            "act": b.data.act.tolist(),
            "sensors": b.sensors.tolist(),
            "target": b.target.tolist(),
            "heading": b.heading,
        }
        obs = {
            kind: {k: v.tolist() for k, v in b.observation(kind, 2, 0.3, 0.1278, 0).items()}
            for kind in ["walking", "flight"]
        }
        fixtures.append({"state": state, "observation": obs})

    for i in range(12):
        capture()
        b.step(speed=2, turn=0.3)
    for _ in range(4500):
        b.step(state="takeoff", speed=6, turn=0, height=2)
    for i in range(12):
        capture()
        b.step(state="flight", speed=10, turn=0.3, height=2)
    b.heading += 2 * np.pi
    capture()
    m, d = b.model, mujoco.MjData(b.model)
    physics = []
    m.opt.timestep = 0.0002
    for _ in range(40):
        mujoco.mj_step(m, d)
        physics.append({"qpos": d.qpos.tolist(), "qvel": d.qvel.tolist(), "act": d.act.tolist()})
    d = mujoco.MjData(m)
    controlled = []
    for i in range(80):
        d.ctrl[:] = 0.2 * np.sin(np.arange(m.nu) * 0.7 + i * 0.13)
        mujoco.mj_step(m, d)
        controlled.append(
            {
                "ctrl": d.ctrl.tolist(),
                "qpos": d.qpos.tolist(),
                "qvel": d.qvel.tolist(),
                "act": d.act.tolist(),
            }
        )
    out = Path("results/body-controller/export/body-validation.json")
    out.write_text(
        json.dumps(
            {
                "observations": fixtures,
                "physics_zero_controls": physics,
                "physics_actuated": controlled,
            }
        )
    )
    print(out)


if __name__ == "__main__":
    main()

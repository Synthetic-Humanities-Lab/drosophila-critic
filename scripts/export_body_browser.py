"""Package frozen float32 policies and upstream wingbeat lookup for local inference."""

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np


def main():
    from flybody.tasks.pattern_generators import WingBeatPatternGenerator

    from critic.body_adapter import CONFIG
    from critic.body_runtime import BodyRuntime

    root = Path("results/body-controller/export")
    out = Path("static/assets/body-v1")
    out.mkdir(exist_ok=True, parents=True)
    Path("static/assets/flybody").mkdir(exist_ok=True, parents=True)
    manifest = {"version": "listening-body-v1", "mujoco": "3.14.0", "files": {}}
    for kind in ["walking", "flight"]:
        with np.load(root / f"{kind}.npz") as data:
            variables = [data[f"v{i}"] for i in range(int(data["n"]))]
            binary = bytearray()
            arrays = []
            for v in variables[:-2]:
                arrays.append({"offset": len(binary), "shape": list(v.shape)})
                binary.extend(v.astype("<f4").tobytes())
            (out / f"{kind}.f32.gz").write_bytes(gzip.compress(bytes(binary), mtime=0))
            (out / f"{kind}.json").write_text(
                json.dumps({"keys": data["keys"].tolist(), "arrays": arrays})
            )
        (out / f"{kind}-observation.json").write_bytes(
            (root / f"{kind}-observation.json").read_bytes()
        )
    wpg = WingBeatPatternGenerator(
        base_pattern_path="results/body-controller/flight-data/wing_pattern_fmech.npy"
    )
    patterns = [
        {k: v.tolist() for k, v in t.items() if k in ["traj", "phase"]} for t in wpg.traj_ctrl
    ]
    (out / "wingbeat.json.gz").write_bytes(
        gzip.compress(
            json.dumps(
                {"patterns": patterns, "frequencies": wpg.beat_freqs.tolist(), "rate": wpg._rate}
            ).encode(),
            mtime=0,
        )
    )
    for name in ["body.xml", "model.json"]:
        (out / name).write_bytes((root / name).read_bytes())
    body = BodyRuntime()
    Path("static/assets/flybody/flybody.glb").write_bytes((root / "flybody.glb").read_bytes())
    import mujoco

    blur = {}
    for side in ["left", "right"]:
        bid = body.id("body", "walker/wing_" + side)
        poses = []
        pattern = body.wpg.traj_ctrl[100]["traj"]
        for phase in [0.1, 0.35, 0.6, 0.85]:
            index = int(np.argmin(np.abs(body.wpg.traj_ctrl[100]["phase"] - phase)))
            body.data.qpos[body.wing_q] = pattern[index]
            mujoco.mj_forward(body.model, body.data)
            poses.append(
                {
                    "position": (body.data.xpos[bid] - body.data.xpos[body.root]).tolist(),
                    "quaternion": body.data.xquat[bid].tolist(),
                }
            )
        blur["walker/wing_" + side] = poses
    Path("static/assets/flybody/wing-blur.json").write_text(json.dumps(blur))
    views = {
        k: {
            n: (v.tolist() if isinstance(v, np.ndarray) else v)
            for n, v in view.items()
            if n != "sensors"
        }
        for k, view in body.views.items()
    }
    for k, view in body.views.items():
        views[k]["sensors"] = {n: ids.tolist() for n, ids in view["sensors"].items()}
    (out / "views.json").write_text(
        json.dumps(
            {
                "views": views,
                "root": body.root,
                "wings": body.wings.tolist(),
                "wing_q": body.wing_q.tolist(),
                "leg_actuators": body.leg_actuators,
                "qpos_spring": body.model.qpos_spring.tolist(),
            }
        )
    )
    (out / "adapter.json").write_text(json.dumps(CONFIG, indent=2) + "\n")
    for p in out.iterdir():
        if p.name == "manifest.json" or not p.is_file():
            continue
        manifest["files"][p.name] = {
            "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }
    for field, name in [
        ("kernel", "static/body-dense.wasm"),
        ("physics", "static/vendor/mujoco/mujoco.wasm"),
    ]:
        p = Path(name)
        manifest[field] = {
            "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }
    manifest["download_bytes"] = (
        sum(f["bytes"] for f in manifest["files"].values())
        + manifest["kernel"]["bytes"]
        + manifest["physics"]["bytes"]
        + 293092
    )
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("Body-processing download bytes", manifest["download_bytes"])


if __name__ == "__main__":
    main()

"""Convert pinned NeuroMechFly meshes to a static, neutral-pose GLB.

Build-only dependencies: trimesh==5.1.0 PyYAML==6.0.3 scipy.
No MuJoCo dynamics or connectome/body registration is implied.
"""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import trimesh
import yaml
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "38c8ec61034cd59bc5ba0de20688d4a3c0000d60"
BASE = f"https://raw.githubusercontent.com/NeLy-EPFL/flygym/{COMMIT}/"
MODEL = "src/flygym/assets/model/neuromechfly/"
CACHE = ROOT / "data" / "fly-body-source"
OUT = ROOT / "static" / "assets" / "fly"
CACHE.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)


def fetch(path):
    target = CACHE / path
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(BASE + path, timeout=60) as response:
            target.write_bytes(response.read())
    return target


rigging = yaml.safe_load(fetch(MODEL + "rigging.yaml").read_text())
pose_path = "src/flygym/assets/pose/pose_neutral.yaml"
# Locate the current neutral-pose filename in the pinned Git tree.
with urlopen(
    f"https://api.github.com/repos/NeLy-EPFL/flygym/git/trees/{COMMIT}?recursive=1"
) as response:
    tree = json.load(response)
pose_path = next(
    x["path"]
    for x in tree["tree"]
    if x["path"].endswith("/neutral.yaml") and "neuromechfly" in x["path"]
)
pose = yaml.safe_load(fetch(pose_path).read_text())
parents = {"c_thorax": None}


def chain(*names):
    parents.update({b: a for a, b in zip(names, names[1:])})


chain("c_thorax", "c_head", "c_rostrum", "c_haustellum")
chain("c_thorax", "c_abdomen12", *[f"c_abdomen{i}" for i in range(3, 7)])
for side in "lr":
    chain("c_head", f"{side}_eye")
    chain("c_head", *[f"{side}_{p}" for p in ["pedicel", "funiculus", "arista"]])
    for part in ["wing", "haltere"]:
        chain("c_thorax", f"{side}_{part}")
    for leg in "fmh":
        chain(
            "c_thorax",
            *[
                f"{side}{leg}_{p}"
                for p in ["coxa", "trochanterfemur", "tibia", *[f"tarsus{i}" for i in range(1, 6)]]
            ],
        )
mesh_paths = {
    name: MODEL
    + "meshes/simplified_max2000faces/"
    + ("l" + name[1:] if name.startswith("r") else name)
    + ".stl"
    for name in parents
}
with ThreadPoolExecutor(max_workers=6) as pool:
    list(pool.map(fetch, sorted(set(mesh_paths.values()))))
scene = trimesh.Scene()
matrices = {}
for name, parent in parents.items():
    info = rigging[name]
    transform = np.eye(4)
    w, x, y, z = info["quat"]
    rotation = Rotation.from_quat([x, y, z, w]).as_matrix()
    for axis in pose["axis_order"]:
        left_name = "l" + name[1:] if name.startswith("r") else name
        left_parent = "l" + parent[1:] if parent and parent.startswith("r") else parent
        angle = pose["joint_angles"].get(f"{left_parent}-{left_name}-{axis}", 0)
        if name.startswith("r") and axis != "pitch":
            angle *= -1
        # FlyGym's joint convention is yaw=X, pitch=Y, roll=Z.
        vec = np.array({"yaw": [1, 0, 0], "pitch": [0, 1, 0], "roll": [0, 0, 1]}[axis])
        rotation = rotation @ Rotation.from_rotvec(vec * np.deg2rad(angle)).as_matrix()
    transform[:3, :3] = rotation
    transform[:3, 3] = info["pos"]
    matrices[name] = (matrices[parent] if parent else np.eye(4)) @ transform
    mesh = trimesh.load_mesh(fetch(mesh_paths[name]))
    mesh.apply_scale([1000, -1000 if name.startswith("r") else 1000, 1000])
    mesh.apply_transform(matrices[name])
    color = [116, 89, 53, 255]
    if "eye" in name:
        color = [109, 48, 34, 255]
    if "wing" in name:
        color = [202, 192, 160, 110]
    mesh.visual = trimesh.visual.TextureVisuals(
        material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=color,
            metallicFactor=0.05,
            roughnessFactor=0.65,
            alphaMode="BLEND" if "wing" in name else "OPAQUE",
            doubleSided=True,
        )
    )
    scene.add_geometry(mesh, node_name=name, geom_name=name)
scene.export(OUT / "fly.glb")
(OUT / "LICENSE.txt").write_bytes(fetch("LICENSE").read_bytes())
(OUT / "NOTICE.txt").write_text(
    f"NeuroMechFly anatomy from NeLy-EPFL/flygym, commit {COMMIT}.\nCopyright 2023–2026 NeuroMechFly v2 Authors. Apache License 2.0.\nModified for The Drosophila Critic: simplified STL meshes converted to GLB; static neutral pose baked; display materials replaced.\nThe micro-CT anatomy is a female exemplar; MaleCNS is a separate male connectome. No anatomical registration or behavioral simulation.\nhttps://github.com/NeLy-EPFL/flygym\n"
)
(OUT / "source.json").write_text(
    json.dumps(
        {
            "repository": "https://github.com/NeLy-EPFL/flygym",
            "commit": COMMIT,
            "pose": pose_path,
            "files": {
                str(p.relative_to(CACHE)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(CACHE.rglob("*"))
                if p.is_file()
            },
            "glb_sha256": hashlib.sha256((OUT / "fly.glb").read_bytes()).hexdigest(),
            "segments": len(parents),
            "bounds_mm": scene.bounds.tolist(),
        },
        indent=2,
    )
)
print(scene.bounds, len(parents), (OUT / "fly.glb").stat().st_size)

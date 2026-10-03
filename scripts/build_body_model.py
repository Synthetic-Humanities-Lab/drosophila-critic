"""Build a combined flybody model; preserve inertia when stripping display meshes."""

import hashlib
import json
import os
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "disable")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/drosophila-mpl")


def glb(model, path):
    import numpy as np

    doc = {
        "asset": {"version": "2.0", "generator": "flybody compiled geometry exporter"},
        "scene": 0,
        "scenes": [{"nodes": []}],
        "nodes": [],
        "meshes": [],
        "materials": [],
        "buffers": [],
        "bufferViews": [],
        "accessors": [],
    }
    binary = bytearray()
    body_nodes = {}
    for b in range(1, model.nbody):
        name = model.id2name(b, "body") or str(b)
        if not name.startswith("walker/"):
            continue
        q = model.body_quat[b]
        node = {
            "name": name,
            "translation": model.body_pos[b].tolist(),
            "rotation": [float(q[1]), float(q[2]), float(q[3]), float(q[0])],
            "children": [],
            "extras": {"body_name": name},
        }
        idx = len(doc["nodes"])
        doc["nodes"].append(node)
        parent = int(model.body_parentid[b])
        if parent in body_nodes:
            doc["nodes"][body_nodes[parent]]["children"].append(idx)
        else:
            doc["scenes"][0]["nodes"].append(idx)
        body_nodes[b] = idx

    def array(values, kind, component):
        a = np.asarray(values, dtype="<f4" if component == 5126 else "<u4")
        offset = len(binary)
        binary.extend(a.tobytes())
        while len(binary) % 4:
            binary.append(0)
        view = len(doc["bufferViews"])
        doc["bufferViews"].append({"buffer": 0, "byteOffset": offset, "byteLength": a.nbytes})
        accessor = {"bufferView": view, "componentType": component, "count": len(a), "type": kind}
        if kind == "VEC3":
            accessor.update(min=a.min(axis=0).tolist(), max=a.max(axis=0).tolist())
        doc["accessors"].append(accessor)
        return len(doc["accessors"]) - 1

    for g in range(model.ngeom):
        b, mesh = int(model.geom_bodyid[g]), int(model.geom_dataid[g])
        if b not in body_nodes or model.geom_group[g] != 1 or mesh < 0:
            continue
        name = model.id2name(g, "geom") or str(g)
        v0, nv = int(model.mesh_vertadr[mesh]), int(model.mesh_vertnum[mesh])
        f0, nf = int(model.mesh_faceadr[mesh]), int(model.mesh_facenum[mesh])
        positions = model.mesh_vert[v0 : v0 + nv]
        faces = model.mesh_face[f0 : f0 + nf]
        positions, inverse = np.unique(positions, axis=0, return_inverse=True)
        faces = inverse[faces]
        # Share vertices without deleting or moving any source triangle.
        vertices = positions
        triangle = positions[faces]
        normals = np.cross(triangle[:, 1] - triangle[:, 0], triangle[:, 2] - triangle[:, 0])
        normal = np.zeros_like(vertices)
        for corner in range(3):
            np.add.at(normal, faces[:, corner], normals)
        normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-20)
        material = int(model.geom_matid[g])
        rgba = model.mat_rgba[material].tolist() if material >= 0 else model.geom_rgba[g].tolist()
        if "membrane" in name:
            rgba = [0.7, 0.73, 0.65, 0.28]
        doc["materials"].append(
            {
                "name": name,
                "pbrMetallicRoughness": {
                    "baseColorFactor": rgba,
                    "metallicFactor": 0,
                    "roughnessFactor": 0.65,
                },
                "doubleSided": True,
                "alphaMode": "BLEND" if rgba[3] < 1 else "OPAQUE",
            }
        )
        doc["meshes"].append(
            {
                "name": name,
                "primitives": [
                    {
                        "attributes": {
                            "POSITION": array(vertices, "VEC3", 5126),
                            "NORMAL": array(normal, "VEC3", 5126),
                        },
                        "indices": array(faces.reshape(-1), "SCALAR", 5125),
                        "material": len(doc["materials"]) - 1,
                    }
                ],
            }
        )
        q = model.geom_quat[g]
        idx = len(doc["nodes"])
        doc["nodes"].append(
            {
                "name": name,
                "mesh": len(doc["meshes"]) - 1,
                "translation": model.geom_pos[g].tolist(),
                "rotation": [float(q[1]), float(q[2]), float(q[3]), float(q[0])],
            }
        )
        doc["nodes"][body_nodes[b]]["children"].append(idx)
    doc["buffers"] = [{"byteLength": len(binary)}]
    header = json.dumps(doc, separators=(",", ":")).encode()
    header += b" " * (-len(header) % 4)
    total = 12 + 8 + len(header) + 8 + len(binary)
    path.write_bytes(
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<I4s", len(header), b"JSON")
        + header
        + struct.pack("<I4s", len(binary), b"BIN\0")
        + binary
    )


def main():
    import mujoco
    import numpy as np
    from flybody.fly_envs import walk_imitation
    from flybody.tasks.constants import _WING_PARAMS

    out = Path("results/body-controller/export")
    out.mkdir(parents=True, exist_ok=True)
    env = walk_imitation(disable_wings=False, random_state=np.random.RandomState(1101))
    # Flight wing actuator and fluid properties from upstream Flying.
    w = env.task._walker
    wing = w.mjcf_model.find("default", "wing").joint
    wing.stiffness, wing.damping = _WING_PARAMS["stiffness"], _WING_PARAMS["damping"]
    for i, axis in enumerate(["yaw", "roll", "pitch"]):
        w.mjcf_model.find("default", axis).general.gainprm[0] = _WING_PARAMS["gainprm"][i]
    for a in w.mjcf_model.find_all("actuator"):
        if "wing" in a.name:
            a.dyntype = "none"
    for g in w.mjcf_model.find_all("geom"):
        if "fluid" in g.name:
            g.fluidshape, g.fluidcoef = "ellipsoid", _WING_PARAMS["fluidcoef"]
    env.reset()
    original = env.physics.model
    initial = {
        original.id2name(j, "joint"): env.physics.data.qpos[
            original.jnt_qposadr[j] : original.jnt_qposadr[j]
            + (7 if original.jnt_type[j] == 0 else 1)
        ].tolist()
        for j in range(original.njnt)
    }
    glb(original, out / "flybody.glb")
    mujoco.mj_saveLastXML(str(out / "full.xml"), original.ptr)
    tree = ET.parse(out / "full.xml")
    root = tree.getroot()
    root.find("compiler").set("inertiafromgeom", "false")
    for parent in root.iter():
        for child in list(parent):
            name = child.get("name", "")
            if name.startswith("ghost/") or (child.tag == "geom" and child.get("mesh") is not None):
                parent.remove(child)
    for b in root.iter("body"):
        name = b.get("name")
        if not name:
            continue
        bid = original.name2id(name, "body")
        if original.body_mass[bid] <= 0:
            continue
        inertia = b.find("inertial")
        if inertia is None:
            inertia = ET.SubElement(b, "inertial")
        inertia.attrib.clear()
        for attr, val in [
            ("pos", original.body_ipos[bid]),
            ("quat", original.body_iquat[bid]),
            ("mass", [original.body_mass[bid]]),
            ("diaginertia", original.body_inertia[bid]),
        ]:
            inertia.set(attr, " ".join(format(float(x), ".17g") for x in val))
    for asset in root.findall("asset"):
        for child in list(asset):
            if child.tag == "mesh":
                asset.remove(child)
    # Remove ghost body exclusions and sites referenced only by recording cameras.
    for contact in root.findall("contact"):
        for c in list(contact):
            if any(v.startswith("ghost/") for v in c.attrib.values()):
                contact.remove(c)
    tree.write(out / "body.xml", encoding="unicode")
    model = mujoco.MjModel.from_xml_path(str(out / "body.xml"))
    data = mujoco.MjData(model)
    for j in range(model.njnt):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j)
        if name in initial:
            values = initial[name]
            data.qpos[model.jnt_qposadr[j] : model.jnt_qposadr[j] + len(values)] = values
    mujoco.mj_forward(model, data)
    names = [
        mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i) or "world" for i in range(model.nbody)
    ]
    masses = [
        (n, abs(float(model.body_mass[i] - original.body_mass[original.name2id(n, "body")])))
        for i, n in enumerate(names)
        if n.startswith("walker/")
    ]
    assert max(v for _, v in masses) < 1e-12
    np.savez(out / "initial.npz", qpos=data.qpos, qvel=data.qvel, act=data.act)
    (out / "model.json").write_text(
        json.dumps(
            {
                "version": "listening-body-v1",
                "units": "centimetres, grams, seconds",
                "source_commit": "d015e9bfe441bd90ae431bac24c55cb74bdbce26",
                "mujoco": mujoco.__version__,
                "sha256": hashlib.sha256((out / "body.xml").read_bytes()).hexdigest(),
                "bodies": names,
                "parents": model.body_parentid.tolist(),
                "qpos": data.qpos.tolist(),
                "qvel": data.qvel.tolist(),
                "act": data.act.tolist(),
                "mass_max_error": max(v for _, v in masses),
            },
            indent=2,
        )
    )
    print(
        "Exported",
        model.nbody,
        "bodies",
        model.nu,
        "actuators",
        (out / "flybody.glb").stat().st_size,
        "GLB bytes",
        flush=True,
    )
    env.close()


if __name__ == "__main__":
    main()

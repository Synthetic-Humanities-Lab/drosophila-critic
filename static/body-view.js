import * as THREE from "./vendor/three.module.js";
import { GLTFLoader } from "./vendor/GLTFLoader.js";

// Recorded MuJoCo body transforms are in centimetres, Z up, quaternion wxyz.
// Physics never runs in this renderer.
export class ArticulatedFly extends THREE.Group {
  constructor(url) {
    super();
    this.nodes = new Map();
    this.antennae = [];
    this.rotation.x = -Math.PI / 2;
    this.ready = Promise.all([
      new GLTFLoader().loadAsync(url),
      fetch(new URL("wing-blur.json", url)).then((r) => {
        if (!r.ok) throw new Error("Wing visualization unavailable");
        return r.json();
      }),
    ]).then(([{ scene }, blurPoses]) => {
      scene.traverse((node) => {
        if (node.userData.body_name)
          this.nodes.set(node.userData.body_name, node);
        if (node.isMesh) {
          node.castShadow = node.receiveShadow = true;
          node.material.roughness = 0.6;
          if (/funiculus|arista/.test(node.name)) this.antennae.push(node);
        }
      });
      this.add(scene);
      this.blurs = [];
      const thorax = this.nodes.get("walker/thorax");
      // Four poses from the published wingbeat pattern form a stable exposure.
      // No low-frequency wing animation is substituted for a 218 Hz beat.
      for (const [name, poses] of Object.entries(blurPoses))
        for (const pose of poses) {
          const blur = this.nodes.get(name).clone(true),
            q = pose.quaternion;
          blur.position.fromArray(pose.position);
          blur.quaternion.set(q[1], q[2], q[3], q[0]);
          blur.visible = false;
          blur.traverse((node) => {
            if (node.isMesh) {
              node.material = node.material.clone();
              node.material.transparent = true;
              node.material.opacity = node.material.opacity < 1 ? 0.07 : 0.16;
              node.material.depthWrite = false;
              node.castShadow = false;
            }
          });
          thorax.add(blur);
          this.blurs.push(blur);
        }
      return this;
    });
    this.a = new THREE.Quaternion();
    this.b = new THREE.Quaternion();
    this.parentQ = new THREE.Quaternion();
    this.p = new THREE.Vector3();
    this.parentP = new THREE.Vector3();
  }
  setFlightBlur(airborne) {
    for (const name of ["walker/wing_left", "walker/wing_right"]) {
      const wing = this.nodes.get(name);
      if (wing) wing.visible = !airborne;
    }
    for (const blur of this.blurs || []) blur.visible = airborne;
  }
  pose(recording, time) {
    const times = recording.time;
    let lo = 0,
      hi = times.length - 1;
    while (lo + 1 < hi) {
      const mid = (lo + hi) >> 1;
      if (times[mid] <= time) lo = mid;
      else hi = mid;
    }
    const alpha = Math.max(
      0,
      Math.min(1, (time - times[lo]) / (times[hi] - times[lo] || 1)),
    );
    const positions = recording.positions,
      rotations = recording.quaternions;
    const position = (i, out) =>
      out
        .fromArray(positions[lo][i])
        .lerp(new THREE.Vector3().fromArray(positions[hi][i]), alpha);
    const rotation = (i, out) => {
      const a = rotations[lo][i],
        b = rotations[hi][i];
      out.set(a[1], a[2], a[3], a[0]);
      this.b.set(b[1], b[2], b[3], b[0]);
      return out.slerp(this.b, alpha);
    };
    recording.body_names.forEach((name, i) => {
      const node = this.nodes.get(name);
      if (!node) return;
      position(i, this.p);
      rotation(i, this.a);
      const parent = recording.body_names.indexOf(
        node.parent?.userData.body_name,
      );
      if (parent >= 0) {
        position(parent, this.parentP);
        rotation(parent, this.parentQ).invert();
        this.p.sub(this.parentP).applyQuaternion(this.parentQ);
        this.a.premultiply(this.parentQ);
      }
      node.position.copy(this.p);
      node.quaternion.copy(this.a);
    });
    const root = recording.body_names.indexOf("walker/thorax");
    const pos = position(root, this.p);
    return {
      position: new THREE.Vector3(pos.x, pos.z, -pos.y),
      state: recording.states[lo],
    };
  }
}

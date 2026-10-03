import * as THREE from "./vendor/three.module.js";
import { ArticulatedFly } from "./body-view.js";
import { FollowCameraTrack } from "./follow-camera.js";

export class EncounterScene {
  constructor(container) {
    this.container = container;
    this.reader = "a";
    this.follow = true;
    this.time = 0;
    this.reduced = matchMedia("(prefers-reduced-motion: reduce)");
    this.reduceMotion = this.reduced.matches;
    this.reduced.addEventListener("change", () =>
      this.setReducedMotion(this.reduced.matches),
    );
    this.locator = document.getElementById("arena-map");
    if (new URLSearchParams(location.search).get("view") === "map") {
      this.fallback();
      return;
    }
    try {
      this.renderer = new THREE.WebGLRenderer({
        antialias: true,
        preserveDrawingBuffer: new URLSearchParams(location.search).has(
          "capture",
        ),
      });
      this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
      this.renderer.shadowMap.enabled = true;
      this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      this.renderer.setClearColor(0x3b4439);
      this.renderer.outputColorSpace = THREE.SRGBColorSpace;
      this.renderer.domElement.setAttribute("role", "img");
      this.renderer.domElement.setAttribute(
        "aria-label",
        "An articulated fly moves through a tabletop listening arena. Its recorded body simulation follows the audio clock.",
      );
      container.append(this.renderer.domElement);
      this.scene = new THREE.Scene();
      this.scene.fog = new THREE.Fog(0x3b4439, 24, 75);
      this.camera = new THREE.PerspectiveCamera(38, 1, 0.005, 150);
      this.scene.add(new THREE.HemisphereLight(0xf9eed2, 0x38483b, 1.8));
      this.sun = new THREE.DirectionalLight(0xffdcad, 2.7);
      this.sun.castShadow = true;
      this.sun.shadow.mapSize.set(2048, 2048);
      this.sun.shadow.bias = -0.000015;
      this.sun.shadow.normalBias = 0.0002;
      this.scene.add(this.sun, this.sun.target);
      this.materials = {};
      this.arena();
      this.actor = this.makeReader();
      this.actor.scale.setScalar(3);
      this.actor.position.set(-15, -0.21, -1);
      this.scene.add(this.actor);
      this.fly = new ArticulatedFly(
        new URL("./assets/flybody/flybody.glb", import.meta.url).href,
      );
      this.scene.add(this.fly);
      this.fly.ready
        .then(() => {
          this.flyReady = true;
          this.container.dataset.ready = "true";
          this.update(this.time, false);
        })
        .catch(() => this.fallback());
      this.renderer.domElement.addEventListener("webglcontextlost", (e) => {
        e.preventDefault();
        this.fallback();
      });
      this.observer = new ResizeObserver(() => this.resize());
      this.observer.observe(container);
      this.resize();
    } catch {
      this.fallback();
    }
  }
  material(color, metal = 0) {
    const key = `${color}-${metal}`;
    return (this.materials[key] ||= new THREE.MeshStandardMaterial({
      color,
      roughness: metal ? 0.35 : 0.86,
      metalness: metal,
    }));
  }
  box(x, y, z, w, h, d, color) {
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(w, h, d),
      this.material(color),
    );
    mesh.position.set(x, y, z);
    mesh.castShadow = mesh.receiveShadow = true;
    return mesh;
  }
  sphere(x, y, z, r, color, scale = [1, 1, 1]) {
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(r, 24, 16),
      this.material(color),
    );
    mesh.position.set(x, y, z);
    mesh.scale.set(...scale);
    mesh.castShadow = true;
    return mesh;
  }
  arena() {
    this.scene.add(this.box(0, -0.23, 0, 38, 0.45, 28, 0x6e725c));
    this.scene.add(this.box(0, -0.012, 0, 20, 0.02, 16, 0xb1b59b));
    const lines = [];
    for (let x = -10; x <= 10; x++) lines.push(x, 0.002, -8, x, 0.002, 8);
    for (let y = -8; y <= 8; y++) lines.push(-10, 0.002, y, 10, 0.002, y);
    const grid = new THREE.LineSegments(
      new THREE.BufferGeometry().setAttribute(
        "position",
        new THREE.Float32BufferAttribute(lines, 3),
      ),
      new THREE.LineBasicMaterial({
        color: 0x68765e,
        transparent: true,
        opacity: 0.13,
      }),
    );
    this.scene.add(grid);
    const corners = [];
    for (const x of [-10, 10])
      for (const z of [-8, 8])
        corners.push(
          x,
          0.012,
          z,
          x - Math.sign(x) * 1,
          0.012,
          z,
          x,
          0.012,
          z,
          x,
          0.012,
          z - Math.sign(z),
          x,
          0.012,
          z,
          x,
          0.65,
          z,
        );
    this.scene.add(
      new THREE.LineSegments(
        new THREE.BufferGeometry().setAttribute(
          "position",
          new THREE.Float32BufferAttribute(corners, 3),
        ),
        new THREE.LineBasicMaterial({ color: 0x334c3f }),
      ),
    );
    this.trail = new THREE.Line(
      new THREE.BufferGeometry(),
      new THREE.LineBasicMaterial({
        color: 0xa36d38,
        transparent: true,
        opacity: 0.48,
      }),
    );
    this.scene.add(this.trail);
    // A book and a microphone establish scale; neither is part of body physics.
    this.scene.add(this.box(-12, 0.12, -1, 1.3, 0.18, 1.8, 0xe2d5a6));
    this.scene.add(this.box(-11.8, 1, -2.7, 0.05, 2, 0.05, 0x343f34));
    this.scene.add(this.sphere(-11.8, 2, -2.7, 0.15, 0x29372f, [1, 1.8, 1]));
  }
  makeReader() {
    const root = new THREE.Group();
    root.position.set(-3.25, 0, -0.35);
    root.rotation.y = Math.PI / 2;
    const body = this.box(0, 1.7, 0, 0.75, 1.05, 0.43, 0x344943);
    root.add(body);
    for (const x of [-0.21, 0.21]) {
      root.add(this.box(x, 0.7, 0, 0.24, 1.1, 0.27, 0x2b3734));
      root.add(this.box(x, 0.17, 0.13, 0.3, 0.2, 0.55, 0x202722));
    }
    const head = new THREE.Group();
    head.position.y = 2.53;
    root.add(head);
    this.head = head;
    this.humanHead = new THREE.Group();
    this.humanHead.add(
      this.sphere(0, 0, 0, 0.33, 0xba8e6d, [0.82, 1.12, 0.82]),
    );
    this.humanHead.add(
      this.sphere(0, 0.21, -0.065, 0.3, 0x423b2d, [0.9, 0.5, 0.95]),
    );
    this.humanHead.add(this.sphere(0, 0, 0.275, 0.085, 0xba8e6d, [0.7, 1, 1]));
    for (const x of [-0.12, 0.12])
      this.humanHead.add(this.sphere(x, 0.06, 0.237, 0.025, 0x292c24));
    head.add(this.humanHead);
    this.robotHead = new THREE.Group();
    const shell = this.box(0, 0, 0, 0.63, 0.59, 0.5, 0xb4bbaa);
    shell.material = this.material(0xb4bbaa, 0.7);
    this.robotHead.add(shell);
    this.robotHead.add(this.box(0, 0.03, 0.26, 0.47, 0.15, 0.025, 0x203b37));
    for (const x of [-0.13, 0.13])
      this.robotHead.add(
        this.box(x, 0.04, 0.28, 0.065, 0.045, 0.018, 0xe9b765),
      );
    this.robotHead.add(this.box(0, 0.43, 0, 0.03, 0.26, 0.03, 0x909b86));
    this.robotHead.add(this.sphere(0, 0.58, 0, 0.065, 0xcb8752));
    head.add(this.robotHead);
    this.arms = [];
    for (const x of [-0.5, 0.5]) {
      const arm = new THREE.Group();
      arm.position.set(x, 2.1, 0);
      arm.add(this.box(0, -0.34, 0.14, 0.2, 0.7, 0.22, 0x4f6357));
      arm.add(this.sphere(0, -0.69, 0.2, 0.12, 0xb4bbaa));
      root.add(arm);
      this.arms.push(arm);
    }
    return root;
  }
  setReader(reader) {
    this.reader = reader;
    if (this.actor) this.actor.visible = reader !== "silence";
    if (this.humanHead) {
      this.humanHead.visible = reader === "b" || reader === "visitor";
      this.robotHead.visible = reader === "a";
    }
    this.render();
  }
  setClose(whole) {
    this.follow = !whole;
    this.update(this.time, false);
  }
  load(recording) {
    this.recording = recording;
    this.time = 0;
    this.rootIndex = recording?.body_names.indexOf("walker/thorax") ?? -1;
    if (this.rootIndex < 0)
      throw new Error("The body recording has no thorax transform.");
    this.cameraTrack = new FollowCameraTrack(recording, this.rootIndex);
    const points = recording.positions
      .filter((_, i) => i % 5 === 0)
      .map(
        (p) =>
          new THREE.Vector3(p[this.rootIndex][0], 0.007, -p[this.rootIndex][1]),
      );
    if (this.trail) {
      this.trail.geometry.dispose();
      this.trail.geometry = new THREE.BufferGeometry().setFromPoints(points);
    }
    this.update(0, false);
  }
  locate(time) {
    const r = this.recording;
    if (!r) return null;
    const {
      frame: { lo },
      position,
      target,
    } = this.cameraTrack.sample(time);
    return {
      index: lo,
      position,
      cameraTarget: target,
      state: r.states[lo],
      airborne: r.airborne?.[lo] ?? r.states[lo] === "flight",
      command: r.commands[lo],
    };
  }
  update(time, playing, displacement = 0, scale = 1) {
    this.time = time;
    const state = this.locate(time);
    this.current = state;
    if (state) {
      const r = this.recording,
        p = state.position;
      const path = r.positions
        .filter((_, i) => i % 10 === 0 && r.time[i] <= time)
        .map(
          (row, i) =>
            `${i ? "L" : "M"}${row[this.rootIndex][0] + 10},${8 - row[this.rootIndex][1]}`,
        )
        .join(" ");
      if (this.locator)
        this.locator.innerHTML = `<rect x=".1" y=".1" width="19.8" height="15.8" fill="none" stroke="#8c9b7f" stroke-width=".1"/><path d="${path}" fill="none" stroke="#ddb273" stroke-width=".12"/><circle cx="${p[0] + 10}" cy="${8 - p[1]}" r=".3" fill="#f0d29e"/><text x="1" y="15" fill="#acb7a1" font-size="1">20 × 16 cm</text>`;
      if (this.flyReady) {
        this.fly.pose(r, time);
        this.fly.setFlightBlur(state.airborne);
      }
      const text = state.airborne
        ? "FLYING"
        : state.state === "takeoff"
          ? "PREPARING TO FLY"
          : state.state.toUpperCase();
      const node = document.getElementById("body-state");
      if (node)
        node.textContent =
          text + (state.command.boundary ? " · ARENA TURN" : "");
      if (this.trail)
        this.trail.geometry.setDrawRange(
          0,
          Math.max(1, Math.floor(state.index / 5)),
        );
    }
    if (!this.renderer || this.failed) return;
    if (this.head) {
      const moving = playing && !this.reduceMotion;
      this.head.rotation.x = moving ? 0.06 * Math.sin(time * 2) : 0.08;
      for (let i = 0; i < this.arms.length; i++)
        this.arms[i].rotation.x =
          -0.55 + (moving ? 0.07 * Math.sin(time * 2 + i) : 0);
    }
    for (const antenna of this.fly.antennae || []) {
      antenna.material.emissive.setHex(0xbb7027);
      antenna.material.emissiveIntensity = this.reduceMotion
        ? 0
        : Math.min(0.6, (displacement / scale) * 0.6);
    }
    const following = this.follow && !this.reduceMotion;
    this.camera.near = following ? 0.005 : 0.2;
    this.camera.updateProjectionMatrix();
    let target = new THREE.Vector3(0, 0.14, 0);
    if (state) {
      const p = state.cameraTarget;
      target.set(p[0], p[2], -p[1]);
    }
    if (following) {
      this.camera.position.copy(target).add(new THREE.Vector3(0.3, 0.32, 0.7));
      this.camera.lookAt(target);
    } else {
      this.camera.position.set(16, 18, 23);
      this.camera.lookAt(-1, 1, 0);
    }
    const lightTarget = following ? target : new THREE.Vector3();
    this.sun.position.copy(lightTarget).add(new THREE.Vector3(-5, 8, 4));
    this.sun.target.position.copy(lightTarget);
    const span = following ? 2 : 17;
    Object.assign(this.sun.shadow.camera, {
      left: -span,
      right: span,
      top: span,
      bottom: -span,
      near: 0.1,
      far: 65,
    });
    this.sun.shadow.camera.updateProjectionMatrix();
    this.render();
  }
  resize() {
    if (!this.renderer) return;
    const { width, height } = this.container.getBoundingClientRect();
    if (!width || !height) return;
    this.renderer.setSize(width, height);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.update(this.time, false);
  }
  setReducedMotion(value) {
    this.reduceMotion = value;
    const control = document.getElementById("camera");
    if (control) {
      control.disabled = this.failed || value;
      control.textContent = value
        ? "Fixed view"
        : this.follow
          ? "Whole arena ↗"
          : "Follow fly ↙";
    }
    this.update(this.time, false);
  }
  render() {
    if (this.renderer && !this.failed)
      this.renderer.render(this.scene, this.camera);
  }
  fallback() {
    this.failed = true;
    document.getElementById("scene-fallback").hidden = false;
    document.getElementById("camera").disabled = true;
    this.container.closest(".stage-wrap").classList.add("arena-fallback");
  }
}

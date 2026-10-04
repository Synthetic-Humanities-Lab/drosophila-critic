import * as THREE from "./vendor/three.module.js";
import { ArticulatedFly } from "./body-view.js";
import { FollowCameraTrack, closeView } from "./follow-camera.js";
import { ListeningRoom } from "./listening-room.js";
import { RecordedPath } from "./recorded-path.js";

export class EncounterScene {
  constructor(container) {
    this.container = container;
    this.wrap = container.closest(".stage-wrap");
    this.reader = "a";
    this.follow = false;
    this.time = 0;
    this.playing = false;
    this.reduced = matchMedia("(prefers-reduced-motion: reduce)");
    this.reduceMotion = this.reduced.matches;
    this.reduced.addEventListener("change", () =>
      this.setReducedMotion(this.reduced.matches),
    );
    this.locator = document.getElementById("arena-map");
    this.locatorPath = this.locator?.querySelector("path");
    this.locatorDot = this.locator?.querySelector("circle");
    this.inset = document.getElementById("fly-closeup");
    this.insetViewport = document.getElementById("fly-closeup-view");
    this.control = document.getElementById("camera");
    if (this.inset) this.inset.onclick = () => this.toggleView();
    if (new URLSearchParams(location.search).get("view") === "map") {
      this.fallback(true);
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
        "A reader speaks into a microphone wired to a glass listening box. The fly and its path replay measured body movement.",
      );
      container.append(this.renderer.domElement);
      this.scene = new THREE.Scene();
      this.scene.fog = new THREE.Fog(0x3b4439, 180, 550);
      this.camera = new THREE.PerspectiveCamera(62, 1, 0.1, 1000);
      this.closeCamera = new THREE.PerspectiveCamera(38, 1, 0.005, 200);
      this.scene.add(new THREE.HemisphereLight(0xf9eed2, 0x38483b, 1.8));
      this.sun = new THREE.DirectionalLight(0xffdcad, 2.7);
      this.sun.castShadow = true;
      this.sun.shadow.mapSize.set(2048, 2048);
      this.sun.shadow.bias = -0.000015;
      this.sun.shadow.normalBias = 0.0002;
      this.scene.add(this.sun, this.sun.target);
      this.room = new ListeningRoom();
      this.scene.add(this.room);
      this.trail = new THREE.Line(
        new THREE.BufferGeometry(),
        new THREE.LineBasicMaterial({
          color: 0x986033,
          transparent: true,
          opacity: 0.8,
        }),
      );
      this.trailTip = new THREE.Line(
        new THREE.BufferGeometry().setAttribute(
          "position",
          new THREE.Float32BufferAttribute(new Float32Array(6), 3),
        ),
        this.trail.material,
      );
      this.scene.add(this.trail, this.trailTip);
      this.fly = new ArticulatedFly(
        new URL("./assets/flybody/flybody.glb", import.meta.url).href,
      );
      this.scene.add(this.fly);
      this.fly.ready
        .then(() => {
          this.flyReady = true;
          this.container.dataset.ready = "true";
          this.update(this.time, this.playing);
        })
        .catch(() => this.fallback());
      this.renderer.domElement.addEventListener("webglcontextlost", (e) => {
        e.preventDefault();
        this.fallback();
      });
      this.observer = new ResizeObserver(() => this.resize());
      this.observer.observe(container);
      this.syncView();
      this.resize();
    } catch {
      this.fallback();
    }
  }
  setReader(reader) {
    this.reader = reader;
    this.room?.setReader(reader);
    this.render();
  }
  toggleView() {
    if (this.failed || this.reduceMotion) return;
    this.follow = !this.follow;
    this.syncView();
    this.resize();
  }
  syncView() {
    this.wrap.dataset.view = this.failed
      ? "map"
      : this.reduceMotion
        ? "fixed"
        : this.follow
          ? "fly"
          : "table";
    this.control.disabled = this.failed || this.reduceMotion;
    this.control.setAttribute(
      "aria-pressed",
      String(this.follow && !this.reduceMotion),
    );
    this.control.textContent = this.reduceMotion
      ? "Fixed view"
      : this.follow
        ? "Whole table ↗"
        : "Follow fly ↗";
    this.control.setAttribute(
      "aria-label",
      this.reduceMotion
        ? "Fixed view: reduced motion enabled"
        : this.follow
          ? "Show the whole table"
          : "Follow the fly closely",
    );
  }
  load(recording) {
    this.recording = recording;
    this.time = 0;
    this.rootIndex = recording?.body_names.indexOf("walker/thorax") ?? -1;
    if (this.rootIndex < 0)
      throw new Error("The body recording has no thorax transform.");
    this.cameraTrack = new FollowCameraTrack(recording, this.rootIndex);
    this.path = new RecordedPath(this.cameraTrack.positions);
    this.wrap.dataset.body = "ready";
    if (this.fly) this.fly.visible = true;
    if (this.trailTip) this.trailTip.visible = true;
    this.locatorDot?.removeAttribute("visibility");
    if (this.trail) {
      this.trail.geometry.dispose();
      this.trail.geometry = new THREE.BufferGeometry().setAttribute(
        "position",
        new THREE.BufferAttribute(this.path.floor, 3),
      );
    }
    this.update(0, false);
  }
  clear() {
    this.recording = null;
    this.cameraTrack = null;
    this.path = null;
    this.wrap.dataset.body = "loading";
    if (this.fly) this.fly.visible = false;
    if (this.trail) this.trail.geometry.setDrawRange(0, 0);
    if (this.trailTip) this.trailTip.visible = false;
    this.locatorPath?.removeAttribute("d");
    this.locatorDot?.setAttribute("visibility", "hidden");
    document.getElementById("body-state").textContent = "LOADING BODY";
    this.update(0, false);
  }
  locate(time) {
    if (!this.recording) return null;
    const sample = this.cameraTrack.sample(time);
    const index = sample.frame.lo;
    return {
      ...sample,
      index,
      state: this.recording.states[index],
      airborne:
        this.recording.airborne?.[index] ??
        this.recording.states[index] === "flight",
      command: this.recording.commands[index],
    };
  }
  update(time, playing, displacement = 0, scale = 1) {
    this.time = time;
    this.playing = playing;
    const state = this.locate(time);
    this.current = state;
    if (state) {
      const path = this.path.sample(state);
      this.locatorPath?.setAttribute("d", path.map);
      this.locatorDot?.setAttribute("cx", state.position[0] + 10);
      this.locatorDot?.setAttribute("cy", 8 - state.position[1]);
      if (this.flyReady) {
        this.fly.pose(this.recording, time);
        this.fly.setFlightBlur(state.airborne);
      }
      const text = state.airborne
        ? "FLYING"
        : state.state === "takeoff"
          ? "PREPARING TO FLY"
          : state.state.toUpperCase();
      const node = document.getElementById("body-state");
      if (node)
        node.textContent = text + (state.command.boundary ? " · BOX TURN" : "");
      if (this.trail) {
        this.trail.geometry.setDrawRange(0, path.count);
        this.trailTip.geometry.attributes.position.array.set(path.tip);
        this.trailTip.geometry.attributes.position.needsUpdate = true;
        this.trailTip.geometry.computeBoundingSphere();
      }
    }
    if (!this.renderer || this.failed) return;
    this.room.animate(time, playing && !this.reduceMotion);
    for (const antenna of this.fly.antennae || []) {
      antenna.material.emissive.setHex(0xbb7027);
      antenna.material.emissiveIntensity = this.reduceMotion
        ? 0
        : Math.min(0.6, (displacement / scale) * 0.6);
    }
    const p = state?.target ?? [0, 0, 0.14];
    const view = closeView(p);
    this.target = new THREE.Vector3(...view.lookAt);
    this.closeCamera.position.fromArray(view.position);
    this.closeCamera.fov = view.fov;
    this.closeCamera.lookAt(this.target);
    this.camera.position.set(-9, 22, 42);
    this.camera.lookAt(-18, 7, -18);
    this.render();
  }
  resize() {
    if (!this.renderer || this.failed) return;
    const { width, height } = this.container.getBoundingClientRect();
    if (!width || !height) return;
    this.width = width;
    this.height = height;
    this.renderer.setSize(width, height);
    this.camera.aspect = width / height;
    // Keep the reader and entire box in frame on a narrow phone screen.
    this.camera.fov = THREE.MathUtils.radToDeg(
      2 *
        Math.atan(
          Math.tan(THREE.MathUtils.degToRad(62 / 2)) *
            Math.max(1, 2 / this.camera.aspect),
        ),
    );
    this.camera.updateProjectionMatrix();
    const inset = this.insetViewport.getBoundingClientRect();
    const stage = this.container.getBoundingClientRect();
    this.insetRect = {
      x: inset.left - stage.left,
      y: stage.bottom - inset.bottom,
      width: inset.width,
      height: inset.height,
    };
    this.closeCamera.aspect = this.follow
      ? width / height
      : inset.width / inset.height || 1;
    this.closeCamera.updateProjectionMatrix();
    this.update(this.time, this.playing);
  }
  setReducedMotion(value) {
    this.reduceMotion = value;
    this.syncView();
    this.resize();
  }
  lighting(close) {
    const centre = close ? this.target : new THREE.Vector3(-15, 0, -15);
    const span = close ? 2 : 95;
    this.sun.position
      .copy(centre)
      .add(new THREE.Vector3(-0.5, 0.8, 0.4).multiplyScalar(close ? 12 : 160));
    this.sun.target.position.copy(centre);
    Object.assign(this.sun.shadow.camera, {
      left: -span,
      right: span,
      top: span,
      bottom: -span,
      near: 0.1,
      far: close ? 35 : 450,
    });
    this.sun.shadow.camera.updateProjectionMatrix();
    this.room.setCutaway(close);
  }
  render() {
    if (!this.renderer || this.failed || !this.width || !this.target) return;
    const following = this.follow && !this.reduceMotion;
    this.renderer.setScissorTest(false);
    this.renderer.setViewport(0, 0, this.width, this.height);
    this.lighting(following);
    this.renderer.render(
      this.scene,
      following ? this.closeCamera : this.camera,
    );
    if (!following && !this.reduceMotion && this.flyReady && this.recording) {
      const { x, y, width, height } = this.insetRect;
      this.renderer.setScissorTest(true);
      this.renderer.setScissor(x, y, width, height);
      this.renderer.setViewport(x, y, width, height);
      this.lighting(true);
      this.renderer.render(this.scene, this.closeCamera);
      this.renderer.setScissorTest(false);
    }
  }
  fallback(manual = false) {
    this.failed = true;
    this.wrap.dataset.view = "map";
    const message = document.getElementById("scene-fallback");
    message.hidden = false;
    if (manual)
      message.textContent =
        "2D view. The map shows the recorded path. Audio and neural measurements still work.";
    this.control.disabled = true;
    this.wrap.classList.add("arena-fallback");
    if (this.renderer) this.renderer.domElement.hidden = true;
  }
}

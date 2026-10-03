import * as THREE from "./vendor/three.module.js";
import { GLTFLoader } from "./vendor/GLTFLoader.js";

// Stage animation is separate from recorded neural state. No behavioral decoder.
export class EncounterScene {
  constructor(container) {
    this.container = container;
    this.reader = "a";
    this.close = false;
    this.reduced = matchMedia("(prefers-reduced-motion: reduce)");
    try {
      this.renderer = new THREE.WebGLRenderer({ antialias: true });
      this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
      this.renderer.shadowMap.enabled = true;
      this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      this.renderer.setClearColor(0x404b40);
      this.renderer.outputColorSpace = THREE.SRGBColorSpace;
      this.renderer.domElement.setAttribute("role", "img");
      this.renderer.domElement.setAttribute(
        "aria-label",
        "A staged reader addresses an anatomical fly across a wooden reading desk. Reader gestures are theatrical.",
      );
      container.append(this.renderer.domElement);
      this.scene = new THREE.Scene();
      this.scene.fog = new THREE.Fog(0x404b40, 15, 33);
      this.camera = new THREE.PerspectiveCamera(36, 1, 0.1, 60);
      this.scene.add(new THREE.HemisphereLight(0xe5eed3, 0x403b29, 1.5));
      const sun = new THREE.DirectionalLight(0xffe0bd, 3.2);
      sun.position.set(-4, 10, 5);
      sun.castShadow = true;
      sun.shadow.mapSize.set(2048, 2048);
      Object.assign(sun.shadow.camera, {
        left: -9,
        right: 9,
        top: 9,
        bottom: -9,
      });
      sun.shadow.bias = -0.001;
      this.scene.add(sun);
      this.scene.add(sun.target);
      const fill = new THREE.DirectionalLight(0xa8c6dd, 1.3);
      fill.position.set(6, 3, -3);
      this.scene.add(fill);
      this.materials = {};
      this.floor();
      this.table();
      this.props();
      this.actor = this.makeReader();
      this.scene.add(this.actor);
      this.setReader(this.reader);
      const plinth = this.box(0, 1.52, 0, 3.2, 0.18, 2.5, 0x333d30);
      this.scene.add(plinth);
      new GLTFLoader().load(
        new URL("./assets/fly/fly.glb", import.meta.url).href,
        (gltf) => {
          this.fly = gltf.scene;
          // Asset uses Z-up; theatre uses Y-up. Fit it from actual bounds.
          this.fly.rotation.x = -Math.PI / 2;
          this.fly.rotation.z = -Math.PI / 2;
          this.fly.updateMatrixWorld(true);
          let bounds = new THREE.Box3().setFromObject(this.fly),
            size = bounds.getSize(new THREE.Vector3());
          this.fly.scale.setScalar(2.65 / Math.max(size.x, size.z));
          this.fly.updateMatrixWorld(true);
          bounds = new THREE.Box3().setFromObject(this.fly);
          const center = bounds.getCenter(new THREE.Vector3());
          this.fly.position.set(-center.x, 1.64 - bounds.min.y, -center.z);
          this.antennae = [];
          this.fly.traverse((node) => {
            if (!node.isMesh) return;
            node.castShadow = true;
            node.receiveShadow = true;
            if (/funiculus|arista/.test(node.name)) {
              node.material = node.material.clone();
              this.antennae.push(node);
            }
          });
          this.scene.add(this.fly);
          this.render();
          this.container.dataset.ready = "true";
        },
        undefined,
        () => this.fallback(),
      );
      this.renderer.domElement.addEventListener("webglcontextlost", (event) => {
        event.preventDefault();
        this.fallback();
      });
      this.renderer.domElement.addEventListener("webglcontextrestored", () => {
        document.getElementById("scene-fallback").hidden = true;
        document.getElementById("camera").disabled = false;
        this.render();
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
      roughness: metal ? 0.35 : 0.88,
      metalness: metal,
    }));
  }
  box(x, y, z, w, h, d, color) {
    const m = new THREE.Mesh(
      new THREE.BoxGeometry(w, h, d),
      this.material(color),
    );
    m.position.set(x, y, z);
    m.castShadow = true;
    m.receiveShadow = true;
    return m;
  }
  sphere(x, y, z, r, color, scale = [1, 1, 1]) {
    const m = new THREE.Mesh(
      new THREE.SphereGeometry(r, 24, 16),
      this.material(color),
    );
    m.position.set(x, y, z);
    m.scale.set(...scale);
    m.castShadow = true;
    return m;
  }
  floor() {
    const plane = this.box(0, -0.13, 0, 35, 0.25, 35, 0x55604c);
    this.scene.add(plane);
    for (let i = -10; i <= 10; i++)
      this.scene.add(this.box(i * 1.25, 0, 0, 0.015, 0.005, 28, 0x46503e));
    this.scene.add(this.box(0, 3, -5.5, 22, 6, 0.2, 0x687660));
    for (let i = -2; i <= 2; i++)
      this.scene.add(this.box(i * 3, 3, -5.35, 0.07, 6, 0.08, 0x485442));
  }
  table() {
    for (let i = 0; i < 7; i++)
      this.scene.add(
        this.box(
          0,
          1.35,
          -1.8 + i * 0.6,
          7.5,
          0.2,
          0.58,
          i % 2 ? 0x75613e : 0x82704b,
        ),
      );
    for (const x of [-3.1, 3.1])
      for (const z of [-1.45, 1.45])
        this.scene.add(this.box(x, 0.6, z, 0.17, 1.4, 0.17, 0x30392d));
  }
  props() {
    const book = new THREE.Group();
    book.add(this.box(0, 0, 0, 1.1, 0.07, 0.8, 0xd8cfab));
    book.add(this.box(0, 0.04, 0, 0.012, 0.008, 0.8, 0x867651));
    book.position.set(-2.05, 1.53, 0.35);
    book.rotation.z = 0.15;
    this.scene.add(book);
    for (let i = 0; i < 6; i++) {
      const line = this.box(
        -2.05,
        1.58,
        0.1 + i * 0.08,
        0.65,
        0.006,
        0.006,
        0x75715b,
      );
      this.scene.add(line);
    }
    const lamp = new THREE.Group();
    lamp.add(this.box(0, 0, 0, 0.5, 0.1, 0.45, 0x27352c));
    lamp.add(this.box(0, 0.65, 0, 0.035, 1.3, 0.035, 0x7c8069));
    const shade = new THREE.Mesh(
      new THREE.ConeGeometry(0.4, 0.45, 24, 1, true),
      this.material(0x35483a),
    );
    shade.position.y = 1.32;
    lamp.add(shade);
    lamp.position.set(2.5, 1.48, -1.05);
    this.scene.add(lamp);
    const bulb = new THREE.PointLight(0xffd492, 5, 4, 2);
    bulb.position.set(2.5, 2.65, -1.05);
    this.scene.add(bulb);
    for (let i = 0; i < 3; i++)
      this.scene.add(
        this.box(
          2.5,
          1.51 + i * 0.075,
          0.9,
          0.7,
          0.07,
          0.45,
          [0x435647, 0xb39767, 0x6b624d][i],
        ),
      );
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
  setClose(close) {
    this.close = close;
    this.resize();
  }
  update(time, playing, displacement = 0, displacementScale = 1) {
    if (!this.renderer) return;
    const moving = playing && !this.reduced.matches;
    if (this.head) {
      this.head.rotation.x = moving ? 0.06 * Math.sin(time * 2) : 0.08;
      this.head.rotation.y = moving ? 0.04 * Math.sin(time * 0.7) : 0;
      this.arms.forEach((arm, i) => {
        arm.rotation.x =
          -0.55 +
          (moving
            ? (this.reader === "b" ? 0.22 : 0.055) * Math.sin(time * 2 + i)
            : 0);
      });
    }
    // Envelope intensity marks modeled vibration; it is not a fabricated oscillation.
    for (const antenna of this.antennae || []) {
      antenna.material.emissive.setHex(0xbb7027);
      antenna.material.emissiveIntensity = Math.min(
        0.65,
        this.reduced.matches ? 0 : (displacement / displacementScale) * 0.65,
      );
    }
    this.render();
  }
  resize() {
    if (!this.renderer) return;
    const { width, height } = this.container.getBoundingClientRect();
    if (!width || !height) return;
    this.renderer.setSize(width, height);
    this.camera.aspect = width / height;
    if (this.close) {
      this.camera.position.set(3.1, 3.05, 4.3);
      this.camera.lookAt(-0.25, 2.05, 0);
    } else {
      this.camera.position
        .set(5.0, 4.25, 6.8)
        .multiplyScalar(width < 500 ? 1.1 : 1);
      this.camera.lookAt(-0.6, 1.75, 0);
    }
    this.camera.updateProjectionMatrix();
    this.render();
  }
  render() {
    if (this.renderer && this.scene)
      this.renderer.render(this.scene, this.camera);
  }
  fallback() {
    document.getElementById("scene-fallback").hidden = false;
    document.getElementById("camera").disabled = true;
  }
}

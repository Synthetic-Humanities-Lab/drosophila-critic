import * as THREE from "./vendor/three.module.js";

// Centimetres, matching the unscaled flybody recording. Only the scenery is staged.
export class ListeningRoom extends THREE.Group {
  constructor() {
    super();
    this.materials = {};
    this.build();
    this.actor = this.makeReader();
    this.actor.scale.setScalar(50);
    this.actor.position.set(-73, -97, -59);
    this.actor.rotation.y = 0.48;
    this.add(this.actor);
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
  tube(points, radius, color) {
    const curve = new THREE.CatmullRomCurve3(
      points.map((p) => new THREE.Vector3(...p)),
    );
    const mesh = new THREE.Mesh(
      new THREE.TubeGeometry(curve, 48, radius, 8, false),
      this.material(color),
    );
    mesh.castShadow = true;
    return mesh;
  }
  build() {
    this.add(this.box(-37.5, -1.65, -18, 150, 3, 58, 0x84846b));
    for (const x of [-105, 30])
      for (const z of [-40, 7])
        this.add(this.box(x, -40, z, 4, 74, 4, 0x4b5745));
    this.add(this.box(0, -77.1, 0, 700, 0.2, 700, 0x4c5847));
    this.add(this.box(0, -0.18, 0, 20.7, 0.34, 16.7, 0x56634e));
    this.add(this.box(0, -0.015, 0, 20, 0.025, 16, 0xb5b69c));

    this.enclosure = new THREE.Group();
    const glass = new THREE.MeshStandardMaterial({
      color: 0xd6e0c9,
      transparent: true,
      opacity: 0.065,
      roughness: 0.2,
      metalness: 0.08,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    for (const x of [-10.1, 10.1]) {
      const pane = new THREE.Mesh(new THREE.PlaneGeometry(16.2, 10), glass);
      pane.rotation.y = Math.PI / 2;
      pane.position.set(x, 5, 0);
      this.enclosure.add(pane);
    }
    for (const z of [-8.1, 8.1]) {
      const pane = new THREE.Mesh(new THREE.PlaneGeometry(20.2, 10), glass);
      pane.position.set(0, 5, z);
      this.enclosure.add(pane);
    }
    const lid = new THREE.Mesh(new THREE.PlaneGeometry(20.2, 16.2), glass);
    lid.rotation.x = -Math.PI / 2;
    lid.position.y = 10.1;
    this.enclosure.add(lid);
    for (const x of [-10.15, 10.15])
      for (const z of [-8.15, 8.15])
        this.enclosure.add(this.box(x, 5, z, 0.22, 10.2, 0.22, 0x304a3d));
    for (const y of [0, 10.1]) {
      for (const x of [-10.15, 10.15])
        this.enclosure.add(this.box(x, y, 0, 0.22, 0.22, 16.4, 0x304a3d));
      for (const z of [-8.15, 8.15])
        this.enclosure.add(this.box(0, y, z, 20.4, 0.22, 0.22, 0x304a3d));
    }
    this.add(this.enclosure);

    // The speaker sits outside the existing movement volume; it adds no collider.
    this.speaker = new THREE.Group();
    this.speaker.position.set(-7.2, 4.5, -9);
    this.speaker.add(this.box(0, 0, 0, 3.2, 4.2, 1.6, 0x354a3c));
    const cone = new THREE.Mesh(
      new THREE.CylinderGeometry(1.2, 0.9, 0.25, 32),
      this.material(0x1e2b25),
    );
    cone.rotation.x = Math.PI / 2;
    cone.position.z = 0.89;
    this.speaker.add(cone);
    this.add(this.speaker);

    const book = new THREE.Group();
    book.position.set(-69, 0.45, -28);
    book.rotation.y = -0.12;
    for (const side of [-1, 1]) {
      const page = this.box(side * 4.2, 0, 0, 8.4, 0.65, 11, 0xdfd4b1);
      page.rotation.z = side * 0.05;
      book.add(page);
    }
    book.add(this.box(0, -0.48, 0, 17.5, 0.2, 11.6, 0x8f6748));
    this.add(book);
    this.add(this.sphere(-58, 0.3, -27, 2, 0x263b32, [1, 0.18, 1]));
    this.add(
      this.tube(
        [
          [-58, 0.5, -27],
          [-58, 12, -27],
          [-61, 23, -29],
          [-66, 27, -40],
        ],
        0.3,
        0x293e32,
      ),
    );
    const mic = this.sphere(-66, 27, -40, 1.4, 0x23372e, [1, 1, 1.8]);
    mic.rotation.y = 0.65;
    this.add(mic);
    this.add(
      this.tube(
        [
          [-58, 0.16, -27],
          [-52, 0.16, -24],
          [-38, 0.16, -18],
          [-18, 0.16, -15],
          [-7.2, 0.16, -11],
          [-7.2, 4.5, -9.9],
        ],
        0.12,
        0x29382d,
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
      root.add(this.box(x, 1.3, 0.26, 0.24, 0.27, 0.65, 0x2b3734));
      root.add(this.box(x, 0.95, 0.52, 0.23, 0.7, 0.25, 0x2b3734));
      root.add(this.box(x, 0.5, 0.67, 0.3, 0.2, 0.55, 0x202722));
    }
    root.add(this.box(0, 1.08, -0.02, 1.1, 0.16, 0.9, 0x3d493b));
    root.add(this.box(0, 1.65, -0.45, 1.1, 1, 0.12, 0x3d493b));
    for (const x of [-0.43, 0.43])
      for (const z of [-0.35, 0.3])
        root.add(this.box(x, 0.7, z, 0.08, 0.6, 0.08, 0x303b32));
    const head = new THREE.Group();
    head.position.y = 2.53;
    root.add(head);
    this.head = head;
    head.scale.setScalar(0.72);
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
    this.actor.visible = reader !== "silence";
    this.humanHead.visible = reader === "b" || reader === "visitor";
    this.robotHead.visible = reader === "a";
  }
  animate(time, playing) {
    this.head.rotation.x = playing ? 0.12 + 0.035 * Math.sin(time * 2) : 0.12;
    for (let i = 0; i < this.arms.length; i++)
      this.arms[i].rotation.x =
        -1 + (playing ? 0.025 * Math.sin(time * 2 + i) : 0);
  }
  setCutaway(value) {
    this.enclosure.visible = !value;
  }
}

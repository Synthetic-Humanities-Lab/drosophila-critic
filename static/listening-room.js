import * as THREE from "./vendor/three.module.js";

// The wide camera is fitted to the approved 1073 × 445 scene composition.
// Narrow screens retain that horizontal field of view.
export function tableView(aspect) {
  return {
    position: [29.9986, 22.9402, 74.6205],
    lookAt: [-32.1028, 7.1177, -2.1458],
    fov: THREE.MathUtils.radToDeg(
      2 *
        Math.atan(
          Math.tan(THREE.MathUtils.degToRad(28.4176 / 2)) *
            Math.max(1, 1073 / 445 / aspect),
        ),
    ),
  };
}

// Centimetres, matching the unscaled flybody recording. Only the scenery is staged.
export class ListeningRoom extends THREE.Group {
  constructor() {
    super();
    this.materials = {};
    this.reader = "a";
    this.build();
    this.actor = this.makeReader();
    this.actor.scale.setScalar(32);
    this.actor.position.set(-110, -63, -22);
    this.actor.rotation.y = 1.38;
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
    const curve = Array.isArray(points)
      ? new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(...p)))
      : points;
    const mesh = new THREE.Mesh(
      new THREE.TubeGeometry(curve, 48, radius, 8, false),
      this.material(color),
    );
    mesh.castShadow = true;
    return mesh;
  }
  build() {
    this.add(this.box(-17.5, -1.65, -5, 125, 3, 70, 0x878771));
    for (const x of [-76, 36])
      for (const z of [-35, 25])
        this.add(this.box(x, -40, z, 4, 74, 4, 0x4b5745));
    this.add(this.box(0, -77.1, 0, 700, 0.2, 700, 0x4c5847));
    this.add(this.box(-160, 65, -150, 700, 285, 1, 0x485447));
    this.add(this.box(-435, 45, -147, 12, 245, 6, 0x4b5749));
    this.add(this.box(0, -0.18, 0, 20.7, 0.34, 16.7, 0x56634e));
    this.floor = this.box(0, -0.015, 0, 20, 0.025, 16, 0xb5b69c);
    this.add(this.floor);

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
    this.enclosure.traverse((node) => {
      node.castShadow = false;
    });
    this.add(this.enclosure);

    // The speaker sits outside the existing movement volume; it adds no collider.
    this.speaker = new THREE.Group();
    this.speaker.position.set(-10.95, 4.5, -1);
    this.speaker.rotation.y = Math.PI / 2;
    this.speaker.add(this.box(0, 0, 0, 5.2, 4.8, 1.6, 0x354a3c));
    const cone = new THREE.Mesh(
      new THREE.CylinderGeometry(1.7, 1.35, 0.25, 32),
      this.material(0x1e2b25),
    );
    cone.rotation.x = Math.PI / 2;
    cone.position.z = 0.89;
    this.speaker.add(cone);
    this.add(this.speaker);

    const book = new THREE.Group();
    book.name = "reading-book";
    book.position.set(-69.3, 0.5, 1.25);
    book.rotation.y = 1.05;
    for (const side of [-1, 1]) {
      const page = this.box(side * 5.1, 0, 0, 10.2, 0.55, 12, 0xdfd4b1);
      page.rotation.z = side * 0.05;
      book.add(page);
      const surface = new THREE.PlaneGeometry(10.2, 12, 12, 1);
      const positions = surface.attributes.position;
      for (let i = 0; i < positions.count; i++) {
        const x = positions.getX(i);
        const z = positions.getY(i);
        positions.setXYZ(
          i,
          x,
          0.4 + 0.65 * Math.sin((x / 10.2 + 0.5) * Math.PI),
          -z,
        );
      }
      surface.computeVertexNormals();
      const sheet = new THREE.Mesh(surface, this.material(0xd4cbb0));
      sheet.position.x = side * 5.1;
      sheet.receiveShadow = true;
      book.add(sheet);
    }
    book.add(this.box(0, -0.48, 0, 21, 0.2, 12.6, 0x8f6748));
    this.add(book);
    this.add(this.sphere(-55.8, 0.3, -4, 2.4, 0x263b32, [1, 0.18, 1]));
    this.add(
      this.tube(
        [
          [-55.8, 0.5, -4],
          [-55.8, 6, -4],
          [-57, 9.4, -4.5],
          [-68.6, 10.7, -10],
        ],
        0.17,
        0x293e32,
      ),
    );
    const mic = this.sphere(-68.6, 10.7, -10, 0.9, 0x23372e, [1, 1, 1.5]);
    mic.name = "microphone";
    mic.rotation.y = 0.65;
    this.add(mic);
    const cable = new THREE.CurvePath();
    cable.add(
      new THREE.CatmullRomCurve3(
        [
          [-55.8, 0.2, -4],
          [-60, 0.2, -10.3],
          [-46.1, 0.2, -7.8],
          [-30.5, 0.2, -2.7],
          [-23.5, 0.2, -4.5],
          [-20.8, 0.2, -10.6],
        ].map((p) => new THREE.Vector3(...p)),
      ),
    );
    // A separate rise keeps spline overshoot from burying the cable in the table.
    cable.add(
      new THREE.CubicBezierCurve3(
        new THREE.Vector3(-20.8, 0.2, -10.6),
        new THREE.Vector3(-17, 0.2, -9),
        new THREE.Vector3(-14, 4.5, -3),
        new THREE.Vector3(-11.9, 4.5, -1),
      ),
    );
    this.add(this.tube(cable, 0.12, 0x29382d));
  }
  makeReader() {
    const root = new THREE.Group();
    const body = this.box(-0.18, 1.7, 0, 0.75, 1.05, 0.43, 0x536047);
    root.add(body);
    for (const x of [-0.21, 0.21]) {
      root.add(this.box(x, 1.3, 0.26, 0.24, 0.27, 0.65, 0x2b3734));
      root.add(this.box(x, 0.32, 0.52, 0.23, 1.5, 0.25, 0x2b3734));
      root.add(this.box(x, -0.35, 0.67, 0.3, 0.2, 0.55, 0x202722));
    }
    root.add(this.box(0, 1.08, -0.02, 1.1, 0.16, 0.9, 0x3d493b));
    root.add(this.box(0, 1.65, -0.45, 1.1, 1, 0.12, 0x3d493b));
    for (const x of [-0.43, 0.43])
      for (const z of [-0.35, 0.3])
        root.add(this.box(x, 0.33, z, 0.08, 1.54, 0.08, 0x303b32));
    const head = new THREE.Group();
    head.position.y = 2.53;
    root.add(head);
    this.head = head;
    head.scale.setScalar(0.8);
    head.rotation.z = -0.1;
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
    shell.material = this.material(0x878a6f, 0.08);
    this.robotHead.add(shell);
    this.robotHead.add(this.box(0, 0.03, 0.26, 0.47, 0.15, 0.025, 0x203b37));
    for (const x of [-0.13, 0.13])
      this.robotHead.add(
        this.box(x, 0.04, 0.28, 0.065, 0.045, 0.018, 0xe9b765),
      );
    this.robotHead.add(this.box(-0.055, 0.4, 0, 0.03, 0.2, 0.03, 0x909b86));
    this.robotHead.add(this.sphere(-0.055, 0.56, 0, 0.062, 0xcb8752));
    head.add(this.robotHead);
    this.arms = [];
    const poses = [
      [
        [-0.5, 2.2, 0],
        [-0.6, 1.91, 0.65],
        [-0.5, 2.01, 0.97],
      ],
      [
        [0.5, 2.2, 0],
        [0.5, 1.99, 0.48],
        [0.08, 2.01, 0.83],
      ],
    ];
    for (const pose of poses) {
      const arm = new THREE.Group();
      const shoulder = new THREE.Vector3(...pose[0]);
      arm.position.copy(shoulder);
      for (let i = 0; i < 2; i++) {
        const start = new THREE.Vector3(...pose[i]).sub(shoulder);
        const end = new THREE.Vector3(...pose[i + 1]).sub(shoulder);
        const segment = this.box(
          0,
          0,
          0,
          0.14,
          start.distanceTo(end),
          0.16,
          0x4f6357,
        );
        segment.position.copy(start).add(end).multiplyScalar(0.5);
        segment.quaternion.setFromUnitVectors(
          new THREE.Vector3(0, 1, 0),
          end.sub(start).normalize(),
        );
        arm.add(segment);
      }
      const hand = this.sphere(0, 0, 0, 0.075, 0xb4bbaa);
      hand.position.fromArray(pose[2]).sub(shoulder);
      arm.add(hand);
      root.add(arm);
      this.arms.push(arm);
    }
    return root;
  }
  setReader(reader) {
    this.reader = reader;
    this.actor.visible = reader !== "silence";
    this.humanHead.visible = reader === "b" || reader === "visitor";
    this.robotHead.visible = reader === "a";
  }
  animate(time, playing) {
    this.head.rotation.x = playing ? 0.35 + 0.025 * Math.sin(time * 2) : 0.35;
    for (let i = 0; i < this.arms.length; i++)
      this.arms[i].rotation.x = playing ? 0.015 * Math.sin(time * 2 + i) : 0;
  }
  setCutaway(value) {
    for (const child of this.children)
      child.visible = !value || child === this.floor;
    if (!value) this.actor.visible = this.reader !== "silence";
  }
}

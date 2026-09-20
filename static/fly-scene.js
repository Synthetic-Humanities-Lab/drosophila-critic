import * as THREE from './vendor/three.module.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';

// A display adapter only: neither the body nor its appearance feeds the simulation.
export class FlyScene {
  constructor(container) {
    this.container = container; this.ready = false; this.data = null; this.rings = [];
    try {
      this.renderer = new THREE.WebGLRenderer({antialias: true, alpha: true});
      this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
      this.renderer.shadowMap.enabled = true;
      this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
      this.renderer.toneMappingExposure = 1.1;
      this.renderer.domElement.setAttribute('aria-label', 'NeuroMechFly anatomy facing an illustrative speaker; sound rings show audio amplitude, antennal color shows recorded JON activity.');
      this.renderer.domElement.setAttribute('role', 'img');
      container.append(this.renderer.domElement);
      this.renderer.domElement.addEventListener('webglcontextlost', e => { e.preventDefault(); this.fail('3D display interrupted. Audio and measurements remain available.'); });
      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(34, 1, 0.01, 100);
      this.camera.up.set(0, 0, 1);
      this.target = new THREE.Vector3(0.5, 0, 0.65);
      this.setView(false);
      this.scene.add(new THREE.HemisphereLight(0xfff8df, 0x635744, 1.5));
      const key = new THREE.DirectionalLight(0xfff7e9, 2.5);
      key.position.set(1, -3, 7); key.castShadow = true;
      key.shadow.mapSize.set(2048, 2048); key.shadow.camera.left = -5; key.shadow.camera.right = 5;
      key.shadow.camera.top = 5; key.shadow.camera.bottom = -5; key.shadow.bias = -0.0002;
      this.scene.add(key);
      const fill = new THREE.DirectionalLight(0xe2e8ed, 1.2); fill.position.set(-2, 4, 3); this.scene.add(fill);
      const ground = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.ShadowMaterial({color: 0x4c4538, opacity: 0.2}));
      ground.position.z = -0.1; ground.receiveShadow = true; this.scene.add(ground);
      this.buildSpeaker();
      for (let i = 0; i < 5; i++) {
        const ring = new THREE.Mesh(new THREE.RingGeometry(0.96, 1, 48, 1, Math.PI / 2, Math.PI), new THREE.MeshBasicMaterial({color: 0x8a4632, transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false}));
        this.scene.add(ring); this.rings.push(ring);
      }
      this.antennae = [];
      new GLTFLoader().load(new URL('./assets/fly/fly.glb', import.meta.url).href, gltf => {
        this.fly = gltf.scene;
        this.fly.traverse(node => {
          if (!node.isMesh) return;
          node.geometry.computeVertexNormals();
          node.castShadow = !node.name.includes('wing'); node.receiveShadow = true;
          if (node.name.includes('pedicel') || node.name.includes('funiculus')) {
            node.material = node.material.clone(); this.antennae.push(node);
          }
        });
        this.scene.add(this.fly); this.ready = true;
        container.dataset.ready = 'true'; document.getElementById('scene-status').textContent = 'NEUROMECHFLY / ANATOMICAL DISPLAY';
        this.resize(); this.update(this.data);
      }, undefined, () => this.fail('The anatomical asset could not load. Audio and measurements remain available.'));
      this.observer = new ResizeObserver(() => this.resize()); this.observer.observe(container);
    } catch { this.fail('3D is unavailable in this browser. Audio and measurements remain available.'); }
  }
  fail(message) { document.getElementById('scene-status').textContent = message; this.ready = false; }
  setView(dorsal) {
    if (!this.camera) return;
    this.camera.position.copy(dorsal ? new THREE.Vector3(0.5, -0.01, 10) : new THREE.Vector3(1.5, -8, 4.6));
    this.camera.lookAt(this.target); this.update(this.data); this.render();
  }
  buildSpeaker() {
    const speaker = new THREE.Group();
    speaker.position.set(3.05, 0, 0);
    speaker.rotation.z = 0.55;
    this.scene.add(speaker);
    const body = new THREE.Mesh(new THREE.BoxGeometry(0.42, 1, 1.35), new THREE.MeshStandardMaterial({color: 0xd9d5c7, roughness: 0.8}));
    body.position.set(0, 0, 0.62); body.castShadow = true; speaker.add(body);
    const cone = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.30, 0.09, 64), new THREE.MeshStandardMaterial({color: 0x31382f, roughness: 0.9}));
    cone.rotation.z = Math.PI / 2; cone.position.set(-0.25, 0, 0.75); speaker.add(cone);
    const center = new THREE.Mesh(new THREE.SphereGeometry(0.13, 24, 16), new THREE.MeshStandardMaterial({color: 0x878778, roughness: 0.7}));
    center.scale.x = 0.35; center.position.set(-0.32, 0, 0.75); speaker.add(center);
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-2.3, -1.75, -0.095), new THREE.Vector3(-1.3, -1.75, -0.095)]), new THREE.LineBasicMaterial({color: 0x8b8e81}));
    this.scene.add(line);
  }
  resize() {
    const {width, height} = this.container.getBoundingClientRect();
    if (!width || !height || !this.renderer) return;
    this.renderer.setSize(width, height); this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix(); this.render();
  }
  update(data) {
    this.data = data;
    if (!this.renderer || !this.scene || !data) return;
    const amplitude = Math.min(1, data.rms / 0.2);
    const jon = Math.min(1, (data.groups?.['JO-A/B input'] || 0) / 100);
    for (const part of this.antennae || []) {
      part.material.emissive.setHex(0xa84e23); part.material.emissiveIntensity = jon * 1.4;
    }
    for (let i = 0; i < this.rings.length; i++) {
      const phase = ((Math.max(0, data.time) * 1.5 + i / this.rings.length) % 1);
      const ring = this.rings[i];
      ring.position.set(2.65 - phase * 1.5, 0, 0.85);
      ring.quaternion.copy(this.camera.quaternion);
      ring.scale.setScalar(0.20 + phase * 0.44);
      ring.material.opacity = amplitude * (1 - phase) * 0.85;
    }
    this.render();
  }
  render() { if (this.renderer && this.scene && this.camera) this.renderer.render(this.scene, this.camera); }
}

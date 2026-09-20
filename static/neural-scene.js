import * as THREE from './vendor/three.module.js';

// Recorded coordinates and recorded spikes only. Camera projection is a display choice.
export class NeuralScene {
  constructor(container) {
    this.container = container;
    try {
      this.renderer = new THREE.WebGLRenderer({antialias:true, alpha:true});
      this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
      this.renderer.domElement.setAttribute('role', 'img');
      this.renderer.domElement.setAttribute('aria-label', 'Measured spikes at MaleCNS neuron coordinates. Amber points fired in the current recorded 100 millisecond bin.');
      container.append(this.renderer.domElement);
      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(38,1,.01,20);
      this.camera.position.set(0,0,3.3);
      this.camera.lookAt(0,0,0);
      this.observer = new ResizeObserver(() => this.resize());
      this.observer.observe(container);
    } catch { container.textContent = 'Spatial display unavailable. Recorded measurements remain below.'; }
  }
  load(data) {
    if (!this.renderer || !data.available) return;
    this.data = data; this.lastBin = null;
    if (this.points) {this.scene.remove(this.points); this.points.geometry.dispose(); this.points.material.dispose();}
    const bounds = [0,1,2].map(axis => {
      const values=data.positions.map(p=>p[axis]);
      return [Math.min(...values),Math.max(...values)];
    });
    const span=Math.max(...bounds.map(([a,b])=>b-a));
    const positions=new Float32Array(data.positions.length*3);
    data.positions.forEach((p,i)=>{
      positions[3*i]=(p[0]-(bounds[0][0]+bounds[0][1])/2)/span*2;
      positions[3*i+1]=-(p[2]-(bounds[2][0]+bounds[2][1])/2)/span*2;
      positions[3*i+2]=(p[1]-(bounds[1][0]+bounds[1][1])/2)/span*2;
    });
    this.colors=new Float32Array(positions.length);
    const geometry=new THREE.BufferGeometry();
    geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));
    geometry.setAttribute('color',new THREE.BufferAttribute(this.colors,3));
    this.points=new THREE.Points(geometry,new THREE.PointsMaterial({size:.009,vertexColors:true,sizeAttenuation:true}));
    this.scene.add(this.points);
    document.getElementById('neural-caption').textContent=`${data.displayed_neurons.toLocaleString()} displayed / ${data.mapped_neurons.toLocaleString()} with coordinates. Amber = fired in this 100 ms bin. Fixed sample; no invented connections.`;
    this.resize();this.update(0);
  }
  update(time) {
    if (!this.data || !this.points) return;
    const index=Math.max(0,Math.min(this.data.firing_bins.length-1,Math.floor((time-this.data.start_time)/this.data.bin_seconds)));
    if(index===this.lastBin) return;
    this.lastBin=index;
    for(let i=0;i<this.colors.length;i+=3) {this.colors[i]=.12;this.colors[i+1]=.19;this.colors[i+2]=.21;}
    for(const id of this.data.firing_bins[index]) {this.colors[id*3]=1;this.colors[id*3+1]=.68;this.colors[id*3+2]=.22;}
    this.points.geometry.attributes.color.needsUpdate=true;
    document.getElementById('spatial-count').textContent=`${this.data.firing_bins[index].length.toLocaleString()} sampled neurons firing`;
    this.renderer.render(this.scene,this.camera);
  }
  resize() {
    if(!this.renderer) return;
    const {width,height}=this.container.getBoundingClientRect();
    if(!width||!height)return;
    this.renderer.setSize(width,height);this.camera.aspect=width/height;this.camera.updateProjectionMatrix();this.renderer.render(this.scene,this.camera);
  }
}

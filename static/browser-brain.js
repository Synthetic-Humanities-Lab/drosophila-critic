import { PCG64 } from './browser-random.js';
// Float32 storage and four accumulation partitions reproduce pinned CPU FlyBrain.
// Inputs and fixtures are numeric only; no text enters this module.
const f = Math.fround;
export class BrowserBrain {
  constructor(manifest, arrays) {
    this.m = manifest;
    Object.assign(this, arrays);
    this.n = manifest.neurons;
    this.v = new Float32Array(this.n);
    this.partial = new Float32Array(this.n * 4);
    this.reset(1101);
  }
  reset(seed) {
    this.v.fill(0);
    this.fired = new Uint32Array(0);
    const state = this.m.random_states[String(seed)];
    if (!state) throw new Error('Seed is not included in the model manifest');
    this.rng = new PCG64(state);
  }
  step(amount, noiseIndices = null) {
    const { n, v, partial, indptr, indices, weights } = this,
      c = this.m.configuration;
    partial.fill(0);
    const chunk = Math.ceil(this.fired.length / 4);
    for (let t = 0; t < 4; t++) {
      const offset = t * n;
      for (
        let k = t * chunk;
        k < Math.min(this.fired.length, (t + 1) * chunk);
        k++
      ) {
        const j = this.fired[k];
        for (let e = indptr[j]; e < indptr[j + 1]; e++) {
          const i = offset + indices[e];
          partial[i] = f(partial[i] + weights[e]);
        }
      }
    }
    for (let i = 0; i < n; i++) {
      let current = f(0);
      for (let t = 0; t < 4; t++) current = f(current + partial[t * n + i]);
      v[i] = f(f(v[i] * c.decay) + (f(current * c.gain) + c.tonic));
    }
    if (noiseIndices !== null) {
      for (const i of noiseIndices) v[i] = f(v[i] + f(c.noise_amplitude));
    } else {
      for (let i = 0; i < n; i++)
        if (this.rng.next() < c.noise_probability)
          v[i] = f(v[i] + f(c.noise_amplitude));
    }
    for (const i of this.m.ear) v[i] = f(v[i] + f(amount));
    const fired = [];
    for (let i = 0; i < n; i++)
      if (v[i] >= 1) {
        fired.push(i);
        v[i] = 0;
      }
    this.fired = Uint32Array.from(fired);
    return this.fired;
  }
}

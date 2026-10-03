// Frozen SavedModel mean network: dense → layer norm → tanh → ELU layers.
export class BodyPolicy {
  constructor(metadata, bytes, kernel) {
    this.keys = [...metadata.keys].sort();
    this.kernel = kernel;
    this.memory = new Float32Array(kernel.memory.buffer);
    this.memory.set(new Float32Array(bytes));
    this.arrays = metadata.arrays.map(({ offset, shape }) => ({
      pointer: offset,
      shape,
      data: new Float32Array(
        kernel.memory.buffer,
        offset,
        shape.reduce((a, b) => a * b, 1),
      ),
    }));
    const offset = (bytes.byteLength + 15) & ~15;
    this.buffers = [
      new Float32Array(kernel.memory.buffer, offset, 1024),
      new Float32Array(kernel.memory.buffer, offset + 4096, 1024),
    ];
  }
  infer(observation) {
    let source = this.buffers[0],
      target = this.buffers[1],
      count = 0;
    for (const key of this.keys) {
      const values = observation[key];
      if (!values) throw new Error(`Missing body observation: ${key}`);
      source.set(values, count);
      count += values.length;
    }
    const a = this.arrays;
    const dense = (bias, weights) => {
      if (weights.shape[0] !== count)
        throw new Error("Body policy observation shape mismatch.");
      const n = weights.shape[1];
      this.kernel.dense(
        source.byteOffset,
        weights.pointer,
        target.byteOffset,
        count,
        n,
      );
      for (let j = 0; j < n; j++) target[j] += bias.data[j];
      [source, target] = [target, source];
      count = n;
    };
    dense(a[0], a[1]);
    let mean = 0,
      variance = 0;
    for (let j = 0; j < count; j++) mean += source[j];
    mean /= count;
    for (let j = 0; j < count; j++) variance += (source[j] - mean) ** 2;
    const scale = 1 / Math.sqrt(variance / count + 1e-5);
    for (let j = 0; j < count; j++)
      source[j] = Math.tanh(
        (source[j] - mean) * scale * a[3].data[j] + a[2].data[j],
      );
    for (let layer = 4; layer < a.length - 2; layer += 2) {
      dense(a[layer], a[layer + 1]);
      for (let j = 0; j < count; j++)
        if (source[j] < 0) source[j] = Math.expm1(source[j]);
    }
    dense(a.at(-2), a.at(-1));
    return source.slice(0, count);
  }
}

export class WingPattern {
  constructor(data) {
    this.data = data;
    this.reset();
  }
  reset() {
    this.frequency = 218;
    this.frequencyIndex = 100;
    this.index = 0;
  }
  step(requested) {
    const { patterns, frequencies, rate } = this.data;
    this.index = (this.index + 1) % patterns[this.frequencyIndex].traj.length;
    this.frequency = this.frequency * rate + requested * (1 - rate);
    const closest = (values, value, phase = false) => {
      let best = 0,
        error = Infinity;
      for (let i = 0; i < values.length; i++) {
        const delta = Math.abs((phase ? values[i] % 1 : values[i]) - value);
        if (delta < error) {
          error = delta;
          best = i;
        }
      }
      return best;
    };
    const index = closest(frequencies, this.frequency);
    if (index !== this.frequencyIndex) {
      this.index = closest(
        patterns[index].phase,
        patterns[this.frequencyIndex].phase[this.index] % 1,
        true,
      );
      this.frequencyIndex = index;
    }
    return patterns[this.frequencyIndex].traj[this.index];
  }
}

// Recording is observational: this module never changes a brain or draws randomness.
export class NeuralCapture {
  constructor(manifest) {
    this.groups = Object.entries(manifest.groups);
    if (this.groups.length > 31)
      throw new Error("Too many monitored populations");
    this.memberships = new Uint32Array(manifest.neurons);
    this.groups.forEach(([, ids], g) => {
      for (const id of ids) this.memberships[id] |= 1 << g;
    });
    this.display = manifest.display_neurons || [];
    this.lookup = new Int32Array(manifest.neurons).fill(-1);
    this.display.forEach((id, index) => {
      this.lookup[id] = index;
    });
    this.active = new Uint8Array(this.display.length);
    this.rows = [];
    this.bins = [];
  }
  step(fired, last = false) {
    const row = Array(this.groups.length).fill(0);
    for (const id of fired) {
      const mask = this.memberships[id];
      if (mask)
        for (let g = 0; g < row.length; g++) if (mask & (1 << g)) row[g]++;
      const display = this.lookup[id];
      if (display >= 0) this.active[display] = 1;
    }
    this.rows.push(row);
    if (this.rows.length % 5 === 0 || last) {
      const bin = [];
      for (let i = 0; i < this.active.length; i++)
        if (this.active[i]) bin.push(i);
      this.bins.push(bin);
      this.active.fill(0);
    }
  }
  result() {
    return {
      group_counts: this.rows,
      group_names: this.groups.map(([name]) => name),
      group_sizes: this.groups.map(([, ids]) => ids.length),
      spatial: {
        firing_bins: this.bins,
        bin_seconds: 0.1,
        neuron_indices: this.display,
      },
    };
  }
}

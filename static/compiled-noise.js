import { BrowserBrain } from "./browser-brain.js";
import { sha256 } from "./content-hash.js";

export const NOISE_KERNEL_SHA256 =
  "f2cbb5dcb8c892e2054ec8123b905005612cd72b389fb2864a41981e3ae8fad6";

export async function loadNoiseKernel(signal) {
  const url = new URL("./neural-noise.wasm", import.meta.url);
  url.searchParams.set("v", NOISE_KERNEL_SHA256);
  const response = await fetch(url, { signal });
  if (!response.ok)
    throw new Error(
      "The neural calculation module could not load. Please retry.",
    );
  const bytes = await response.arrayBuffer();
  if ((await sha256(bytes)) !== NOISE_KERNEL_SHA256)
    throw new Error(
      "The neural calculation module failed its checksum. Reload the page.",
    );
  return (await WebAssembly.instantiate(bytes)).instance;
}

// Only noise generation is compiled. Synaptic sums, voltages, thresholds and
// reset remain in the Python-validated reference implementation.
export class CompiledNoise {
  constructor(instance, neurons) {
    if (!Number.isSafeInteger(neurons) || neurons < 1 || neurons > 0x3fffffff)
      throw new Error("Invalid noise population size.");
    this.kernel = instance.exports;
    this.neurons = neurons;
    this.output = new Uint32Array(neurons);
  }
  reset(state) {
    const value = BigInt(state.state),
      increment = BigInt(state.inc);
    this.kernel.reset(
      BigInt.asUintN(64, value),
      value >> 64n,
      BigInt.asUintN(64, increment),
      increment >> 64n,
    );
  }
  indices(probability) {
    if (!Number.isFinite(probability) || probability < 0 || probability > 1)
      throw new Error("Invalid neural noise probability.");
    let count = 0;
    for (let base = 0; base < this.neurons; base += 32) {
      let mask = this.kernel.mask(
        Math.min(32, this.neurons - base),
        probability,
      );
      while (mask) {
        const bit = mask & -mask;
        this.output[count++] = base + 31 - Math.clz32(bit);
        mask ^= bit;
      }
    }
    return this.output.subarray(0, count);
  }
}

export class CompiledNoiseBrain extends BrowserBrain {
  constructor(manifest, arrays, instance) {
    super(manifest, arrays);
    this.noise = new CompiledNoise(instance, this.n);
    this.reset(1101);
  }
  reset(seed) {
    super.reset(seed);
    this.noise?.reset(this.m.random_states[String(seed)]);
  }
  step(amount, noiseIndices = null) {
    return super.step(
      amount,
      noiseIndices ??
        this.noise.indices(this.m.configuration.noise_probability),
    );
  }
}

// Run after export_browser_model.py has produced the Python reference fixtures.
import fs from "node:fs/promises";
import path from "node:path";
import zlib from "node:zlib";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { BrowserBrain } from "../static/browser-brain.js";
import { NeuralCapture } from "../static/neural-capture.js";
import {
  CompiledNoiseBrain,
  NOISE_KERNEL_SHA256,
} from "../static/compiled-noise.js";

const root = process.argv[2] || "results/browser-benchmark";
const output =
  process.argv[3] || "output/visitor-speed/neural-equivalence.json";
const manifest = JSON.parse(
  await fs.readFile(path.join(root, "manifest.json")),
);
const hash = (data) => createHash("sha256").update(data).digest("hex");
async function load(spec) {
  const bytes = new Uint8Array(spec.length * 4);
  let offset = 0;
  for (const part of spec.parts) {
    const compressed = await fs.readFile(path.join(root, part.file));
    assert.equal(hash(compressed), part.sha256);
    const raw = zlib.gunzipSync(compressed);
    assert.equal(raw.length, part.raw_bytes);
    bytes.set(raw, offset);
    offset += raw.length;
  }
  assert.equal(hash(bytes), spec.sha256);
  return spec.dtype === "float32"
    ? new Float32Array(bytes.buffer)
    : new Uint32Array(bytes.buffer);
}
const arrays = {};
for (const [name, spec] of Object.entries(manifest.arrays))
  arrays[name] = await load(spec);
const noise = await load(manifest.fixture.noise);
const kernel = await fs.readFile("static/neural-noise.wasm");
assert.equal(hash(kernel), NOISE_KERNEL_SHA256);
const original = new BrowserBrain(manifest, arrays);
const compiled = new CompiledNoiseBrain(
  manifest,
  arrays,
  (await WebAssembly.instantiate(kernel)).instance,
);
const trials = [];
for (const [name, brain, supplied] of [
  ["compiled-supplied-noise", compiled, true],
  ["original", original, false],
  ["compiled", compiled, false],
  ["compiled-repeat", compiled, false],
  ["original-repeat", original, false],
]) {
  brain.reset(manifest.fixture.seed);
  const started = performance.now();
  for (const [i, expected] of manifest.fixture.expected.entries()) {
    brain.step(
      expected.input,
      supplied
        ? noise.subarray(
            manifest.fixture.offsets[i],
            manifest.fixture.offsets[i + 1],
          )
        : null,
    );
    assert.equal(
      hash(brain.v),
      expected.voltage_sha256,
      `${name}, voltage, step ${i}`,
    );
    assert.equal(
      hash(brain.fired),
      expected.spikes_sha256,
      `${name}, spikes, step ${i}`,
    );
  }
  trials.push({
    name,
    seconds: (performance.now() - started) / 1000,
    exact_steps: manifest.fixture.expected.length,
  });
}
assert.equal(hash(arrays.weights), manifest.arrays.weights.sha256);
const controlRoot = "static/assets/silence-v1";
const control = JSON.parse(
  await fs.readFile(path.join(controlRoot, "manifest.json")),
);
for (const [key, spec] of Object.entries(manifest.arrays))
  assert.equal(control.contract.arrays[key], spec.sha256);
const capture = new NeuralCapture({
  neurons: manifest.neurons,
  groups: control.contract.groups,
  display_neurons: control.neural.spatial.neuron_indices,
});
compiled.reset(control.contract.seed);
const controlStarted = performance.now();
let steps = 0;
for (const part of control.chunks) {
  const compressed = await fs.readFile(path.join(controlRoot, part.file));
  assert.equal(hash(compressed), part.sha256);
  const chunk = JSON.parse(zlib.gunzipSync(compressed));
  assert.equal(steps, chunk.start);
  for (let i = 0; i < part.steps; i++, steps++) {
    const fired = compiled.step(0);
    capture.step(fired, steps === control.steps - 1);
    assert.equal(fired.length, chunk.counts[i], `silence count, step ${steps}`);
    assert.deepEqual(
      capture.rows.at(-1),
      chunk.group_counts[i],
      `silence populations, step ${steps}`,
    );
    const displayed = [];
    for (const id of fired)
      if (capture.lookup[id] >= 0) displayed.push(capture.lookup[id]);
    assert.deepEqual(
      displayed,
      chunk.firing_steps[i],
      `silence display, step ${steps}`,
    );
  }
}
assert.equal(steps, control.steps);
const report = {
  passed: true,
  node: process.version,
  neurons: manifest.neurons,
  connections: arrays.weights.length,
  kernel_sha256: NOISE_KERNEL_SHA256,
  trials,
  saved_silence: {
    steps,
    exact: true,
    seconds: (performance.now() - controlStarted) / 1000,
  },
};
await fs.mkdir(path.dirname(output), { recursive: true });
await fs.writeFile(output, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify(report, null, 2));

import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { PCG64 } from "../static/browser-random.js";
import { BrowserBrain } from "../static/browser-brain.js";
import {
  CompiledNoise,
  CompiledNoiseBrain,
  loadNoiseKernel,
  NOISE_KERNEL_SHA256,
} from "../static/compiled-noise.js";

const bytes = await readFile(
  new URL("../static/neural-noise.wasm", import.meta.url),
);
const { fixtures } = JSON.parse(
  await readFile(new URL("./pcg64-stream-fixtures.json", import.meta.url)),
);
const instance = async () => (await WebAssembly.instantiate(bytes)).instance;
const hash = (data) => createHash("sha256").update(data).digest("hex");
const state = (kernel) =>
  BigInt.asUintN(64, kernel.stateLo()) +
  (BigInt.asUintN(64, kernel.stateHi()) << 64n);

test("compiled PCG64 matches every Python float and final state for four million samples", async () => {
  assert.equal(hash(bytes), NOISE_KERNEL_SHA256);
  for (const fixture of fixtures) {
    const noise = new CompiledNoise(await instance(), 166700);
    assert.equal(
      noise.kernel.memory,
      undefined,
      "the noise kernel must not reserve a WebAssembly memory",
    );
    noise.reset(fixture.initial);
    const samples = new DataView(new ArrayBuffer(fixture.count * 8));
    for (let i = 0; i < fixture.count; i++)
      samples.setFloat64(i * 8, noise.kernel.next(), true);
    assert.equal(
      hash(new Uint8Array(samples.buffer)),
      fixture.float64_le_sha256,
    );
    assert.equal(state(noise.kernel).toString(), fixture.final.state);
  }
});

test("mask batches retain bit 31 and consume only the final partial batch", async () => {
  for (const neurons of [1, 31, 32, 33, 64, 65]) {
    const noise = new CompiledNoise(await instance(), neurons);
    noise.reset(fixtures[0].initial);
    assert.deepEqual(
      Array.from(noise.indices(1)),
      Array.from({ length: neurons }, (_, i) => i),
    );
    const reference = new PCG64(fixtures[0].initial);
    for (let i = 0; i < neurons; i++) reference.next();
    assert.equal(noise.kernel.next(), reference.next());
  }
});

test("batching preserves draw order, every threshold decision, resets and carry overflow", async () => {
  const neurons = 166700;
  for (const initial of [
    fixtures[0].initial,
    {
      state: ((1n << 128n) - 1n).toString(),
      inc: ((1n << 128n) - 1n).toString(),
    },
  ]) {
    const noise = new CompiledNoise(await instance(), neurons);
    noise.reset(initial);
    const reference = new PCG64(initial);
    for (const probability of [0, 0.024, 1, 0.5]) {
      const expected = [];
      for (let i = 0; i < neurons; i++)
        if (reference.next() < probability) expected.push(i);
      assert.deepEqual(Array.from(noise.indices(probability)), expected);
    }
    const expectedState = reference.state.reduce(
      (value, limb, i) => value + (BigInt(limb) << BigInt(i * 16)),
      0n,
    );
    assert.equal(state(noise.kernel), expectedState);
    noise.reset(initial);
    assert.equal(noise.kernel.next(), new PCG64(initial).next());
    for (const p of [-1, 2, NaN, Infinity])
      assert.throws(() => noise.indices(p), /probability/);
  }
});

test("compiled noise preserves neural voltages and spikes, including supplied noise and reset", async () => {
  const manifest = {
    neurons: 5,
    ear: [0],
    random_states: { 1101: fixtures[0].initial, 1102: fixtures[1].initial },
    configuration: {
      decay: 0.8187307715415955,
      gain: 3,
      tonic: 0.14,
      noise_probability: 0.024,
      noise_amplitude: 0.22,
    },
  };
  const arrays = {
    indptr: new Uint32Array([0, 2, 3, 4, 5, 6]),
    indices: new Uint32Array([1, 2, 2, 3, 4, 0]),
    weights: new Float32Array([0.25, -0.1, 0.4, 0.2, 0.5, 0.3]),
  };
  const original = new BrowserBrain(manifest, arrays),
    compiled = new CompiledNoiseBrain(manifest, arrays, await instance());
  for (const seed of [1101, 1102, 1101]) {
    original.reset(seed);
    compiled.reset(seed);
    for (let i = 0; i < 1000; i++) {
      const supplied = i % 9 === 0 ? new Uint32Array([0, 3]) : null;
      assert.deepEqual(
        compiled.step(i % 3 ? 0.8 : 0, supplied),
        original.step(i % 3 ? 0.8 : 0, supplied),
      );
      assert.deepEqual(compiled.v, original.v);
    }
  }
});

test("kernel loading rejects corrupt, missing and cancelled assets", async (t) => {
  const original = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = original;
  });
  globalThis.fetch = async (url) => {
    assert.equal(url.searchParams.get("v"), NOISE_KERNEL_SHA256);
    return new Response(bytes);
  };
  assert.ok((await loadNoiseKernel()).exports.mask);
  globalThis.fetch = async () => new Response("corrupt");
  await assert.rejects(loadNoiseKernel(), /checksum/);
  globalThis.fetch = async () => new Response("missing", { status: 404 });
  await assert.rejects(loadNoiseKernel(), /could not load/);
  globalThis.fetch = async (_url, { signal }) => {
    signal.throwIfAborted();
  };
  const abort = new AbortController();
  abort.abort();
  await assert.rejects(loadNoiseKernel(abort.signal), { name: "AbortError" });
});

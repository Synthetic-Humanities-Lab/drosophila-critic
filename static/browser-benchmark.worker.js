import { BrowserBrain } from "./browser-brain.js";
import { PCG64 } from "./browser-random.js";
import { NeuralCapture } from "./neural-capture.js";
let brain,
  manifest,
  cancelled = false,
  busy = false,
  cache = null,
  controller = null,
  loadedBytes = 0;
let captureGroups = {};
const hash = async (bytes) =>
  Array.from(
    new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    (b) => b.toString(16).padStart(2, "0"),
  ).join("");
async function loadArray(spec, base) {
  const result = new Uint8Array(spec.length * 4);
  let bytes = 0;
  for (const part of spec.parts) {
    if (cancelled) throw new Error("Cancelled");
    const url = new URL(part.file, base);
    let response = cache ? await cache.match(url) : null;
    const cached = Boolean(response);
    if (!response) {
      response = await fetch(url, { signal: controller?.signal });
    }
    if (!response.ok)
      throw new Error(`Missing model chunk (${response.status})`);
    const compressed = await response.arrayBuffer();
    if ((await hash(compressed)) !== part.sha256) {
      if (cache && cached) await cache.delete(url);
      throw new Error("Model chunk checksum mismatch");
    }
    if (cache && !cached) {
      try {
        await cache.put(url, new Response(compressed));
      } catch {
        cache = null;
      }
    }
    const raw = await new Response(
      new Blob([compressed])
        .stream()
        .pipeThrough(new DecompressionStream("gzip")),
    ).arrayBuffer();
    if (raw.byteLength !== part.raw_bytes)
      throw new Error("Model chunk length mismatch");
    loadedBytes += compressed.byteLength;
    if (bytes + raw.byteLength > result.length)
      throw new Error("Model array length mismatch");
    result.set(new Uint8Array(raw), bytes);
    bytes += raw.byteLength;
    postMessage({
      type: "progress",
      stage: "Loading and checking the fly model",
      fraction: Math.min(1, loadedBytes / manifest.transfer_bytes),
      bytes: loadedBytes,
    });
  }
  if (bytes !== result.length) throw new Error("Model array length mismatch");
  if ((await hash(result)) !== spec.sha256)
    throw new Error("Lossless model checksum mismatch");
  return spec.dtype === "float32"
    ? new Float32Array(result.buffer)
    : new Uint32Array(result.buffer);
}
self.onmessage = async ({ data }) => {
  if (data.type === "cancel") {
    cancelled = true;
    controller?.abort();
    return;
  }
  if (busy) {
    postMessage({ type: "error", message: "A benchmark is already running" });
    return;
  }
  busy = true;
  cancelled = false;
  controller = new AbortController();
  try {
    if (data.type === "initialize") {
      const start = performance.now();
      const base = new URL(data.url, self.location.href);
      loadedBytes = 0;
      const r = await fetch(base, { signal: controller.signal });
      if (!r.ok) throw new Error("Benchmark model export is unavailable");
      manifest = await r.json();
      captureGroups = data.captureGroups || {};
      for (const ids of Object.values(captureGroups))
        if (
          !Array.isArray(ids) ||
          !ids.length ||
          ids.some(
            (id) => !Number.isInteger(id) || id < 0 || id >= manifest.neurons,
          )
        )
          throw new Error("Invalid motor capture population.");
      if (data.cache) {
        try {
          cache = await caches.open(manifest.version);
        } catch {
          cache = null;
        }
      }
      const arrays = {};
      for (const [name, spec] of Object.entries(manifest.arrays))
        arrays[name] = await loadArray(spec, base);
      brain = new BrowserBrain(manifest, arrays);
      postMessage({
        type: "initialized",
        milliseconds: performance.now() - start,
        transfer_bytes: manifest.transfer_bytes,
        connectivity_memory_bytes: manifest.connectivity_memory_bytes,
        working_array_bytes:
          manifest.connectivity_memory_bytes + manifest.neurons * 20,
      });
    } else if (data.type === "validate") {
      if (!brain) throw new Error("Load the model first");
      const base = new URL(data.url, self.location.href);
      const noise = await loadArray(manifest.fixture.noise, base);
      brain.reset(manifest.fixture.seed);
      const mismatches = [];
      for (let i = 0; i < manifest.fixture.expected.length; i++) {
        if (cancelled) throw new Error("Cancelled");
        const e = manifest.fixture.expected[i];
        brain.step(
          e.input,
          noise.subarray(
            manifest.fixture.offsets[i],
            manifest.fixture.offsets[i + 1],
          ),
        );
        const voltage = await hash(brain.v),
          spikes = await hash(brain.fired);
        if (voltage !== e.voltage_sha256 || spikes !== e.spikes_sha256)
          mismatches.push({
            step: i,
            voltage: voltage === e.voltage_sha256,
            spikes: spikes === e.spikes_sha256,
          });
      }
      // A second run generates its own PCG64 noise and must match every Python state.
      brain.reset(manifest.fixture.seed);
      const generatedMismatches = [];
      for (let i = 0; i < manifest.fixture.expected.length; i++) {
        if (cancelled) throw new Error("Cancelled");
        const e = manifest.fixture.expected[i];
        brain.step(e.input);
        if (
          (await hash(brain.v)) !== e.voltage_sha256 ||
          (await hash(brain.fired)) !== e.spikes_sha256
        )
          generatedMismatches.push(i);
        if (i % 10 === 0)
          await new Promise((resolve) => setTimeout(resolve, 0));
      }
      const a = new PCG64(manifest.random_states["1101"]),
        b = new PCG64(manifest.random_states["1101"]);
      let matches = true,
        hits = 0;
      for (let i = 0; i < 1000000; i++) {
        const x = a.next();
        matches &&= x === b.next();
        if (x < manifest.configuration.noise_probability) hits++;
      }
      postMessage({
        type: "validated",
        exact: mismatches.length === 0 && generatedMismatches.length === 0,
        generated_noise_mismatches: generatedMismatches,
        mismatches,
        noise: {
          generator: "PCG64, exact NumPy SeedSequence initial state",
          repeatable: matches,
          observed_probability: hits / 1000000,
          target_probability: manifest.configuration.noise_probability,
        },
        visitor_gate:
          "Numerical gate checked; performance and device qualification still required",
      });
    } else if (data.type === "simulate") {
      if (!brain) throw new Error("Load the model first");
      if (
        !Array.isArray(data.input) ||
        data.input.length > 3300 ||
        !data.input.every((x) => Number.isFinite(x) && x >= 0 && x <= 0.8)
      )
        throw new Error("Invalid acoustic frames");
      brain.reset(data.seed ?? 1101);
      const start = performance.now(),
        counts = [];
      const capture = data.capture
        ? new NeuralCapture({
            ...manifest,
            groups: { ...manifest.groups, ...captureGroups },
          })
        : null;
      for (let i = 0; i < data.input.length; i++) {
        if (cancelled) throw new Error("Cancelled");
        const fired = brain.step(data.input[i]);
        counts.push(fired.length);
        capture?.step(fired, i === data.input.length - 1);
        if (i % 10 === 0) {
          postMessage({
            type: "progress",
            stage: data.label,
            fraction: i / data.input.length,
          });
          await new Promise((resolve) => setTimeout(resolve, 0));
        }
      }
      const weightHash = await hash(brain.weights);
      if (weightHash !== manifest.arrays.weights.sha256)
        throw new Error("Connectome weights changed");
      postMessage({
        type: "result",
        weights_sha256: weightHash,
        label: data.label,
        seconds: performance.now() / 1000 - start / 1000,
        simulated_seconds: data.input.length * manifest.configuration.dt,
        counts,
        seed: data.seed ?? 1101,
        ...(capture?.result() || {}),
      });
    } else throw new Error("Unknown worker request");
  } catch (error) {
    postMessage({
      type: cancelled ? "cancelled" : "error",
      message: error.message,
    });
  } finally {
    busy = false;
  }
};

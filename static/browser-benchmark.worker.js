import { BrowserBrain } from './browser-brain.js';
import { PCG64 } from './browser-random.js';
let brain,
  manifest,
  cancelled = false,
  busy = false;
const hash = async (bytes) =>
  Array.from(
    new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
    (b) => b.toString(16).padStart(2, '0'),
  ).join('');
async function loadArray(spec, base) {
  const chunks = [];
  let bytes = 0;
  for (const part of spec.parts) {
    if (cancelled) throw new Error('Cancelled');
    const response = await fetch(new URL(part.file, base));
    if (!response.ok)
      throw new Error(`Missing model chunk (${response.status})`);
    const compressed = await response.arrayBuffer();
    if ((await hash(compressed)) !== part.sha256)
      throw new Error('Model chunk checksum mismatch');
    const raw = await new Response(
      new Blob([compressed])
        .stream()
        .pipeThrough(new DecompressionStream('gzip')),
    ).arrayBuffer();
    if (raw.byteLength !== part.raw_bytes)
      throw new Error('Model chunk length mismatch');
    chunks.push(new Uint8Array(raw));
    bytes += raw.byteLength;
    postMessage({
      type: 'progress',
      stage: 'Loading verified connectivity',
      bytes,
    });
  }
  const result = new Uint8Array(bytes);
  let at = 0;
  for (const chunk of chunks) {
    result.set(chunk, at);
    at += chunk.length;
  }
  if ((await hash(result)) !== spec.sha256)
    throw new Error('Lossless model checksum mismatch');
  return spec.dtype === 'float32'
    ? new Float32Array(result.buffer)
    : new Uint32Array(result.buffer);
}
self.onmessage = async ({ data }) => {
  if (data.type === 'cancel') {
    cancelled = true;
    return;
  }
  if (busy) {
    postMessage({ type: 'error', message: 'A benchmark is already running' });
    return;
  }
  busy = true;
  cancelled = false;
  try {
    if (data.type === 'initialize') {
      const start = performance.now();
      const base = new URL(data.url, self.location.href);
      const r = await fetch(base);
      if (!r.ok) throw new Error('Benchmark model export is unavailable');
      manifest = await r.json();
      const arrays = {};
      for (const [name, spec] of Object.entries(manifest.arrays))
        arrays[name] = await loadArray(spec, base);
      brain = new BrowserBrain(manifest, arrays);
      postMessage({
        type: 'initialized',
        milliseconds: performance.now() - start,
        transfer_bytes: manifest.transfer_bytes,
        connectivity_memory_bytes: manifest.connectivity_memory_bytes,
        working_array_bytes:
          manifest.connectivity_memory_bytes + manifest.neurons * 20,
      });
    } else if (data.type === 'validate') {
      if (!brain) throw new Error('Load the model first');
      const base = new URL(data.url, self.location.href);
      const noise = await loadArray(manifest.fixture.noise, base);
      brain.reset(manifest.fixture.seed);
      const mismatches = [];
      for (let i = 0; i < manifest.fixture.expected.length; i++) {
        if (cancelled) throw new Error('Cancelled');
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
        if (cancelled) throw new Error('Cancelled');
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
      const a = new PCG64(manifest.random_states['1101']),
        b = new PCG64(manifest.random_states['1101']);
      let matches = true,
        hits = 0;
      for (let i = 0; i < 1000000; i++) {
        const x = a.next();
        matches &&= x === b.next();
        if (x < manifest.configuration.noise_probability) hits++;
      }
      postMessage({
        type: 'validated',
        exact: mismatches.length === 0 && generatedMismatches.length === 0,
        generated_noise_mismatches: generatedMismatches,
        mismatches,
        noise: {
          generator: 'PCG64, exact NumPy SeedSequence initial state',
          repeatable: matches,
          observed_probability: hits / 1000000,
          target_probability: manifest.configuration.noise_probability,
        },
        visitor_gate:
          'Numerical gate checked; performance and device qualification still required',
      });
    } else if (data.type === 'simulate') {
      if (!brain) throw new Error('Load the model first');
      brain.reset(data.seed ?? 1101);
      const start = performance.now(),
        counts = [];
      for (let i = 0; i < data.input.length; i++) {
        if (cancelled) throw new Error('Cancelled');
        counts.push(brain.step(data.input[i]).length);
        if (i % 10 === 0) {
          postMessage({
            type: 'progress',
            stage: data.label,
            fraction: i / data.input.length,
          });
          await new Promise((resolve) => setTimeout(resolve, 0));
        }
      }
      postMessage({
        type: 'result',
        label: data.label,
        seconds: performance.now() / 1000 - start / 1000,
        simulated_seconds: data.input.length * manifest.configuration.dt,
        counts,
        seed: data.seed ?? 1101,
      });
    } else throw new Error('Unknown worker request');
  } catch (error) {
    postMessage({
      type: cancelled ? 'cancelled' : 'error',
      message: error.message,
    });
  } finally {
    busy = false;
  }
};

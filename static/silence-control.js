import { bodyMetrics } from "./body-metrics.js";
import { stableJSON } from "./simulation-contract.js";
import { sha256 } from "./content-hash.js";

export const BODY_FRAME_KEYS = [
  "time",
  "positions",
  "quaternions",
  "states",
  "airborne",
  "commands",
  "inverted",
];

export function silencePrefix(manifest, chunks, steps, duration) {
  if (!Number.isInteger(steps) || steps <= 0 || steps > manifest.steps)
    throw new Error("The saved silence does not cover this recording.");
  const run = { ...manifest.neural, counts: [], group_counts: [] };
  const body = {
    ...manifest.body,
    ...Object.fromEntries(BODY_FRAME_KEYS.map((k) => [k, []])),
  };
  const bins = [],
    active = new Uint8Array(run.spatial.neuron_indices.length);
  let copied = 0;
  for (const chunk of chunks) {
    if (chunk.start !== copied)
      throw new Error("Silence chunks are out of order.");
    const length = chunk.counts.length;
    if (
      chunk.group_counts.length !== length ||
      chunk.firing_steps.length !== length ||
      BODY_FRAME_KEYS.some((k) => chunk.body[k].length !== length)
    )
      throw new Error("Incomplete saved silence chunk.");
    const take = Math.min(length, steps - copied);
    run.counts.push(...chunk.counts.slice(0, take));
    run.group_counts.push(...chunk.group_counts.slice(0, take));
    for (const key of BODY_FRAME_KEYS)
      body[key].push(...chunk.body[key].slice(0, take));
    for (let i = 0; i < take; i++) {
      for (const id of chunk.firing_steps[i]) active[id] = 1;
      copied++;
      if (copied % 5 === 0 || copied === steps) {
        const bin = [];
        for (let j = 0; j < active.length; j++) if (active[j]) bin.push(j);
        bins.push(bin);
        active.fill(0);
      }
    }
    if (copied === steps) break;
  }
  if (copied !== steps) throw new Error("The saved silence is incomplete.");
  run.spatial = { firing_bins: bins, ...run.spatial };
  run.simulated_seconds = steps * manifest.contract.configuration.dt;
  run.seconds = null;
  body.events = body.events.filter((event) => event.time <= body.time.at(-1));
  body.metrics = {
    ...bodyMetrics(
      body,
      body.root_index,
      manifest.contract.baseline_steps * 0.02,
      duration,
    ),
    wall_seconds: null,
  };
  return {
    run,
    body,
    provenance: {
      kind: "precomputed-silence",
      version: manifest.version,
      contract_sha256: manifest.contract_sha256,
      steps,
      duration,
      generation: manifest.generation,
      note: "Exact prefix of the same zero-input simulation; interval measurements recomputed for this recording.",
    },
  };
}

export async function loadSilenceControl(
  contract,
  steps,
  duration,
  { signal, onProgress = () => {} } = {},
) {
  const base = new URL("./assets/silence-v1/", import.meta.url);
  const response = await fetch(new URL("manifest.json", base), { signal });
  if (!response.ok)
    throw new Error(`Saved silence unavailable (${response.status}).`);
  const manifest = await response.json();
  const digest = await sha256(new TextEncoder().encode(stableJSON(contract)));
  if (
    manifest.schema_version !== "saved-silence-v1" ||
    manifest.contract_sha256 !== digest ||
    stableJSON(manifest.contract) !== stableJSON(contract)
  )
    throw new Error("Saved silence belongs to a different simulation version.");
  if (steps > manifest.steps) throw new Error("Saved silence is too short.");
  let cache;
  try {
    cache = await caches.open(manifest.version);
  } catch {
    cache = null;
  }
  const parts = manifest.chunks.filter((part) => part.start < steps),
    chunks = [];
  for (const [index, part] of parts.entries()) {
    signal?.throwIfAborted();
    const url = new URL(part.file, base);
    if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname))
      throw new Error("Invalid silence chunk path.");
    let r = cache ? await cache.match(url) : null;
    const cached = Boolean(r);
    if (!r) r = await fetch(url, { signal });
    if (!r.ok)
      throw new Error(`Saved silence chunk unavailable (${r.status}).`);
    const bytes = await r.arrayBuffer();
    if ((await sha256(bytes)) !== part.sha256) {
      if (cache) await cache.delete(url);
      throw new Error("Saved silence checksum mismatch.");
    }
    if (cache && !cached)
      try {
        await cache.put(url, new Response(bytes));
      } catch {
        cache = null;
      }
    const raw = await new Response(
      new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip")),
    ).arrayBuffer();
    if (raw.byteLength !== part.raw_bytes)
      throw new Error("Saved silence length mismatch.");
    const chunk = JSON.parse(new TextDecoder().decode(raw));
    if (chunk.start !== part.start || chunk.counts.length !== part.steps)
      throw new Error("Invalid saved silence interval.");
    chunks.push(chunk);
    onProgress({
      stage: "Loading the verified silence comparison",
      fraction: (index + 1) / parts.length,
    });
  }
  signal?.throwIfAborted();
  return silencePrefix(manifest, chunks, steps, duration);
}

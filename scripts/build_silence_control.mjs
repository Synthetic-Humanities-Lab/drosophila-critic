// Generate with the same unmodified BrowserBrain and official WASM body runtime.
import fs from "node:fs/promises";
import path from "node:path";
import zlib from "node:zlib";
import crypto from "node:crypto";
import inspector from "node:inspector/promises";
import { BrowserBrain } from "../static/browser-brain.js";
import { NeuralCapture } from "../static/neural-capture.js";
import { simulateBody } from "../static/body-processing.js";
import { loadBodyAssets } from "./body_browser_assets.mjs";
import {
  simulationContract,
  stableJSON,
  LOCAL_SEED,
  BASELINE_STEPS,
  POST_STEPS,
} from "../static/simulation-contract.js";
import { BODY_FRAME_KEYS } from "../static/silence-control.js";

const args = process.argv.slice(2),
  option = (key, fallback) =>
    args.includes(key) ? args[args.indexOf(key) + 1] : fallback;
const output = option("--output", "static/assets/silence-v1");
const duration = Number(option("--seconds", 60));
const hash = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");
const json = async (file) => JSON.parse(await fs.readFile(file));
const model = await json("static/browser-model-v1/manifest.json");
const motor = await json("static/assets/body-v1/capture.json");
const bodyManifest = await json("static/assets/body-v1/manifest.json");
const contract = simulationContract(model, motor, bodyManifest);
const contractHash = hash(stableJSON(contract));
const steps =
  BASELINE_STEPS +
  Math.ceil((duration * 48000) / model.receiver.frame_samples) +
  model.receiver.decay_frames +
  POST_STEPS;
await fs.mkdir(output, { recursive: true });
const arrays = {};
for (const [key, spec] of Object.entries(model.arrays)) {
  const bytes = Buffer.concat(
    await Promise.all(
      spec.parts.map(async (part) => {
        const compressed = await fs.readFile(
          path.join("static/browser-model-v1", part.file),
        );
        if (hash(compressed) !== part.sha256)
          throw new Error("Model chunk checksum mismatch");
        return zlib.gunzipSync(compressed);
      }),
    ),
  );
  if (hash(bytes) !== spec.sha256) throw new Error("Model checksum mismatch");
  const buffer = bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  );
  arrays[key] =
    spec.dtype === "float32"
      ? new Float32Array(buffer)
      : new Uint32Array(buffer);
}
const brain = new BrowserBrain(model, arrays);
const capture = new NeuralCapture({ ...model, groups: contract.groups });
const lookup = new Int32Array(model.neurons).fill(-1);
model.display_neurons.forEach((id, i) => {
  lookup[id] = i;
});
const counts = [],
  firingSteps = [],
  start = performance.now();
brain.reset(LOCAL_SEED);
for (let i = 0; i < steps; i++) {
  const fired = brain.step(0);
  counts.push(fired.length);
  capture.step(fired, i === steps - 1);
  const displayed = [];
  for (const id of fired) if (lookup[id] >= 0) displayed.push(lookup[id]);
  firingSteps.push(displayed);
  if (i % 500 === 0) console.log(`Neural silence ${i}/${steps}`);
}
const run = {
  type: "result",
  seed: LOCAL_SEED,
  counts,
  ...capture.result(),
  weights_sha256: hash(brain.weights),
  seconds: (performance.now() - start) / 1000,
  simulated_seconds: steps * model.configuration.dt,
  label: "Saved silence control",
};
if (run.weights_sha256 !== model.arrays.weights.sha256)
  throw new Error("Weights changed");
await fs.writeFile(
  path.join(output, "neural-reference.json"),
  JSON.stringify(run),
);
const runtime = await loadBodyAssets();
let profiler;
if (args.includes("--profile")) {
  profiler = new inspector.Session();
  profiler.connect();
  await profiler.post("Profiler.enable");
  await profiler.post("Profiler.start");
}
const body = await simulateBody(runtime, runtime.assets.config, run, {
  duration,
  onProgress: ({ simulated_seconds }) => {
    if (Math.round(simulated_seconds * 50) % 500 === 1)
      console.log(`Body silence ${simulated_seconds.toFixed(1)}s`);
  },
});
if (profiler) {
  const { profile } = await profiler.post("Profiler.stop");
  profiler.disconnect();
  const profileDirectory = output.startsWith("static/")
    ? "output/silence-generation"
    : output;
  await fs.mkdir(profileDirectory, { recursive: true });
  await fs.writeFile(
    path.join(profileDirectory, "body.cpuprofile"),
    JSON.stringify(profile),
  );
  const nodes = new Map(profile.nodes.map((n) => [n.id, n.callFrame]));
  const totals = new Map();
  profile.samples.forEach((id, i) => {
    const f = nodes.get(id),
      label = `${f.functionName} @ ${f.url.split("/").at(-1)}:${f.lineNumber + 1}`;
    totals.set(label, (totals.get(label) || 0) + profile.timeDeltas[i] / 1e6);
  });
  console.log(
    "Body profile",
    [...totals].sort((a, b) => b[1] - a[1]).slice(0, 20),
  );
}
await fs.writeFile(
  path.join(output, "body-reference.json"),
  JSON.stringify(body),
);
const manifest = {
  schema_version: "saved-silence-v1",
  version: `silence-${contractHash.slice(0, 16)}`,
  contract,
  contract_sha256: contractHash,
  steps,
  generation: {
    neural_seconds: run.seconds,
    body_seconds: body.metrics.wall_seconds,
    runtime: process.version,
    duration,
  },
  neural: Object.fromEntries(
    Object.entries(run).filter(
      ([key]) => !["counts", "group_counts"].includes(key),
    ),
  ),
  body: Object.fromEntries(
    Object.entries(body).filter(
      ([key]) => ![...BODY_FRAME_KEYS, "metrics"].includes(key),
    ),
  ),
  chunks: [],
  source_sha256: {},
};
delete manifest.neural.spatial.firing_bins;
// Bind the artifact to every implementation affecting inputs, noise, physics or measurements.
for (const file of [
  "browser-brain.js",
  "browser-random.js",
  "neural-capture.js",
  "body-adapter.js",
  "body-runtime.js",
  "body-policy.js",
  "body-processing.js",
  "body-metrics.js",
  "local-audio.js",
  "simulation-contract.js",
])
  manifest.source_sha256[file] = hash(await fs.readFile("static/" + file));
for (let start = 0; start < steps; start += 250) {
  const end = Math.min(steps, start + 250);
  const chunk = {
    start,
    counts: counts.slice(start, end),
    group_counts: run.group_counts.slice(start, end),
    firing_steps: firingSteps.slice(start, end),
    body: Object.fromEntries(
      BODY_FRAME_KEYS.map((key) => [key, body[key].slice(start, end)]),
    ),
  };
  const raw = Buffer.from(JSON.stringify(chunk)),
    compressed = zlib.gzipSync(raw, { level: 9 });
  const file = `${String(start).padStart(4, "0")}-${hash(compressed).slice(0, 12)}.json.gz`;
  await fs.writeFile(path.join(output, file), compressed);
  manifest.chunks.push({
    start,
    steps: end - start,
    file,
    sha256: hash(compressed),
    bytes: compressed.byteLength,
    raw_bytes: raw.byteLength,
  });
}
manifest.transfer_bytes = manifest.chunks.reduce(
  (sum, part) => sum + part.bytes,
  0,
);
await fs.writeFile(
  path.join(output, "manifest.json"),
  JSON.stringify(manifest),
);
console.log(
  JSON.stringify(
    {
      steps,
      transfer_bytes: manifest.transfer_bytes,
      generation: manifest.generation,
      output,
    },
    null,
    2,
  ),
);
// Large uncompressed references are local evidence only, never public assets.
if (output.startsWith("static/")) {
  await fs.rm(path.join(output, "neural-reference.json"));
  await fs.rm(path.join(output, "body-reference.json"));
}

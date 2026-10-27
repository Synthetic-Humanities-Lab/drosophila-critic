// Slow release check: complete transitions and the full saved silence trajectory.
import fs from "node:fs/promises";
import assert from "node:assert/strict";
import { gunzipSync } from "node:zlib";
import { createHash } from "node:crypto";
import { loadBodyAssets } from "./body_browser_assets.mjs";
import loadOptimized from "../static/vendor/mujoco-simd/mujoco.js";
import { BODY_PHYSICS_BUILD } from "../static/body-physics.js";
import { simulateBody } from "../static/body-processing.js";
import { NeuralBodyAdapter } from "../static/body-adapter.js";
import { createBodyPolicies } from "../static/body-policy-bundle.js";
import { silencePrefix, BODY_FRAME_KEYS } from "../static/silence-control.js";

const output = process.argv[2] || "output/body-speed/physics-equivalence.json";
const reference = await loadBodyAssets();
const optimized = {
  ...reference,
  mj: await loadOptimized({
    wasmBinary: await fs.readFile("static/vendor/mujoco-simd/mujoco.wasm"),
  }),
};
const metadata = {},
  weights = {};
for (const kind of ["walking", "flight"]) {
  metadata[kind] = JSON.parse(
    await fs.readFile(`static/assets/body-v1/${kind}.json`),
  );
  const raw = gunzipSync(
    await fs.readFile(`static/assets/body-v1/${kind}.f32.gz`),
  );
  weights[kind] = raw.buffer.slice(
    raw.byteOffset,
    raw.byteOffset + raw.byteLength,
  );
}
const { instance } = await WebAssembly.instantiate(
  await fs.readFile("static/body-dense.wasm"),
);
optimized.policies = createBodyPolicies(metadata, weights, instance.exports);
const hash = (value) =>
  createHash("sha256").update(JSON.stringify(value)).digest("hex");
const comparable = (body) => ({
  ...Object.fromEntries(
    [...BODY_FRAME_KEYS, "events"].map((key) => [key, body[key]]),
  ),
  metrics: Object.fromEntries(
    Object.entries(body.metrics).filter(([key]) => key !== "wall_seconds"),
  ),
});
const names = Object.keys(new NeuralBodyAdapter(reference.assets.config).r);
// Same controlled-rate sequence as the original Python arena proof.
const diagnostic = {
  seed: 1101,
  group_names: names,
  group_sizes: names.map(() => 50),
  group_counts: Array.from({ length: 550 }, (_, frame) => {
    const t = frame * 0.02;
    return names.map((name) => {
      if (name === "motor_walk") return t < 2 ? 5 : t > 8 ? 4 : 0;
      if (name === "motor_turn_left") return t > 1 && t < 2 ? 3 : 0;
      if (name === "motor_takeoff") return frame === 105 ? 25 : 0;
      if (name === "motor_flight") return t > 2 && t < 5 ? 3 : 0;
      if (name === "motor_flight_left") return t > 2 && t < 5 ? 4 : 0;
      return 0;
    });
  }),
};
const report = { build: BODY_PHYSICS_BUILD, node: process.version, checks: [] };
const run = (runtime, input, duration, baseline) =>
  simulateBody(runtime, runtime.assets.config, input, {
    duration,
    baseline,
    onProgress: (p) => {
      if (Math.round(p.simulated_seconds * 50) % 500 === 1)
        console.log(p.simulated_seconds);
    },
  });
const before = await run(reference, diagnostic, 8, 0);
const after = await run(optimized, diagnostic, 8, 0);
assert.deepEqual(comparable(after), comparable(before));
for (const state of ["walking", "takeoff", "flight", "landing"])
  assert.ok(
    after.states.includes(state),
    `The diagnostic must exercise ${state}`,
  );
report.checks.push({
  name: "eleven-second controlled movement",
  frames: after.time.length,
  states: [...new Set(after.states)],
  exact: true,
  hash: hash(comparable(after)),
  before_seconds: before.metrics.wall_seconds,
  after_seconds: after.metrics.wall_seconds,
});
console.log(report.checks.at(-1));
const base = "static/assets/silence-v1/";
const manifest = JSON.parse(await fs.readFile(base + "manifest.json"));
const chunks = [];
for (const part of manifest.chunks) {
  const bytes = await fs.readFile(base + part.file);
  assert.equal(createHash("sha256").update(bytes).digest("hex"), part.sha256);
  chunks.push(JSON.parse(gunzipSync(bytes)));
}
const saved = silencePrefix(
  manifest,
  chunks,
  manifest.steps,
  manifest.generation.duration,
);
const actual = await run(
  optimized,
  saved.run,
  manifest.generation.duration,
  1.5,
);
assert.deepEqual(comparable(actual), comparable(saved.body));
report.checks.push({
  name: "complete saved silence",
  frames: actual.time.length,
  simulated_seconds: saved.run.simulated_seconds,
  exact: true,
  hash: hash(comparable(actual)),
  seconds: actual.metrics.wall_seconds,
});
report.passed = true;
await fs.writeFile(output, JSON.stringify(report, null, 2) + "\n");
console.log(report);

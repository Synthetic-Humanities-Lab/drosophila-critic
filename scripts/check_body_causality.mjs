import fs from "node:fs/promises";
import crypto from "node:crypto";
import { loadBodyAssets } from "./body_browser_assets.mjs";
import { simulateBody } from "../static/body-processing.js";
const runtime = await loadBodyAssets();
const names = [
  "walk",
  "turn_left",
  "turn_right",
  "takeoff",
  "flight",
  "flight_left",
  "flight_right",
].map((n) => "motor_" + n);
const control = (stimulated, clamped = false) => ({
  seed: 1101,
  group_names: names,
  group_sizes: names.map(() => 2),
  group_counts: Array.from({ length: 50 }, (_, i) =>
    names.map((_, j) =>
      stimulated && !clamped && j === 0 && i % 5 === 0 ? 1 : 0,
    ),
  ),
});
const report = {
  description:
    "Controlled one-second motor capture: walking stimulation, zero input, and the same stimulation clamped to zero before the adapter. No poem input.",
  runs: {},
};
for (const [name, run] of Object.entries({
  zero: control(false),
  stimulated: control(true),
  clamped: control(true, true),
})) {
  const body = await simulateBody(runtime, runtime.assets.config, run, {
    baseline: 0,
    duration: 1,
  });
  report.runs[name] = {
    metrics: body.metrics,
    pose_sha256: crypto
      .createHash("sha256")
      .update(JSON.stringify([body.positions, body.quaternions]))
      .digest("hex"),
  };
}
report.passed =
  report.runs.zero.pose_sha256 === report.runs.clamped.pose_sha256 &&
  report.runs.stimulated.pose_sha256 !== report.runs.zero.pose_sha256 &&
  report.runs.stimulated.metrics.distance_walked_cm >
    report.runs.zero.metrics.distance_walked_cm + 0.1;
await fs.writeFile(
  "experiments/body-controller-v2/body-causality.json",
  JSON.stringify(report, null, 2) + "\n",
);
console.log(report);
if (!report.passed) process.exitCode = 1;

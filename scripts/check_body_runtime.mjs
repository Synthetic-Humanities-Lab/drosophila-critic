import fs from "node:fs/promises";
import { loadBodyAssets } from "./body_browser_assets.mjs";
import { BodyRuntime } from "../static/body-runtime.js";

const { mj, assets, policies } = await loadBodyAssets(),
  b = new BodyRuntime(mj, assets, policies);
const fixture = JSON.parse(
  await fs.readFile("results/body-controller/export/body-validation.json"),
);
let obsError = 0,
  physicsError = 0,
  actuatedError = 0;
const compare = (actual, expected) =>
  Math.max(...actual.map((x, i) => Math.abs(x - expected[i])));
for (const f of fixture.observations) {
  b.d.qpos.set(f.state.qpos);
  b.d.qvel.set(f.state.qvel);
  b.d.act.set(f.state.act);
  mj.mj_forward(b.m, b.d);
  b.sensors = f.state.sensors;
  b.target = f.state.target;
  b.heading = f.state.heading;
  for (const kind of ["walking", "flight"]) {
    const obs = b.observation(kind, 2, 0.3, 0.1278, 0);
    for (const key in obs)
      obsError = Math.max(
        obsError,
        compare(obs[key], f.observation[kind][key].flat(Infinity)),
      );
  }
}
const d = new mj.MjData(b.m);
b.m.opt.timestep = 0.0002;
for (const expected of fixture.physics_zero_controls) {
  mj.mj_step(b.m, d);
  for (const key of ["qpos", "qvel", "act"])
    physicsError = Math.max(
      physicsError,
      compare(Array.from(d[key]), expected[key]),
    );
}
d.delete();
const controlled = new mj.MjData(b.m);
const actuatedFields = Object.fromEntries(
  ["qpos", "qvel", "act"].map((k) => [k, { absolute: 0, normalized: 0 }]),
);
for (const expected of fixture.physics_actuated) {
  controlled.ctrl.set(expected.ctrl);
  mj.mj_step(b.m, controlled);
  for (const key of ["qpos", "qvel", "act"]) {
    actuatedError = Math.max(
      actuatedError,
      compare(Array.from(controlled[key]), expected[key]),
    );
    for (let i = 0; i < expected[key].length; i++) {
      const error = Math.abs(controlled[key][i] - expected[key][i]);
      actuatedFields[key].absolute = Math.max(
        actuatedFields[key].absolute,
        error,
      );
      actuatedFields[key].normalized = Math.max(
        actuatedFields[key].normalized,
        error / (1 + Math.abs(expected[key][i])),
      );
    }
  }
}
controlled.delete();
b.dispose();
const report = {
  observation_fixtures: fixture.observations.length,
  observation_max_absolute_error: obsError,
  physics_40_steps_max_absolute_error: physicsError,
  actuated_80_steps_max_absolute_error: actuatedError,
  actuated_fields: actuatedFields,
  tolerance:
    "Absolute tolerances: observations 1e-8; zero controls 1e-7; actuated qpos 1e-8 cm/rad, qvel 1e-6 cm/s or rad/s, act 1e-12. Native and WASM solvers are not bit-identical.",
  passed:
    obsError < 1e-8 &&
    physicsError < 1e-7 &&
    actuatedFields.qpos.absolute < 1e-8 &&
    actuatedFields.qvel.absolute < 1e-6 &&
    actuatedFields.act.absolute < 1e-12,
};
const run = () => {
  const body = new BodyRuntime(mj, assets, policies),
    start = performance.now();
  for (let i = 0; i < 500; i++) body.step({ speed: 2, turn: 0.3 });
  const result = {
    seconds: (performance.now() - start) / 1000,
    position: Array.from(body.position),
    qpos: Array.from(body.d.qpos),
  };
  body.dispose();
  return result;
};
const first = run(),
  second = run();
Object.assign(report, {
  one_second_walk_wall_seconds: first.seconds,
  repeatable: JSON.stringify(first.qpos) === JSON.stringify(second.qpos),
  position: first.position,
});
report.passed &&= report.repeatable;
console.log(report);
await fs.writeFile(
  "results/body-controller/export/browser-runtime-parity.json",
  JSON.stringify(report, null, 2),
);
if (!report.passed) process.exitCode = 1;

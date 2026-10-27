import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { createHash } from "node:crypto";
import { bodyStepping } from "../static/body-stepping.js";
import { BodyRuntime } from "../static/body-runtime.js";
import { loadBodyAssets } from "../scripts/body_browser_assets.mjs";
import loadCurrent from "../static/vendor/mujoco-body-v2/mujoco.js";

// The reuse boundary relies on this audited runtime changing only ctrl and dt
// between forward and step. A runtime edit requires reviewing that boundary.
test("the audited body runtime still owns the same mutation boundary", async () => {
  const source = await fs.readFile(
    new URL("../static/body-runtime.js", import.meta.url),
  );
  assert.equal(
    createHash("sha256").update(source).digest("hex"),
    "a15690b6747c6fe2206525c689b8d70a088c530606fec83f4a04a5fb6ab16d9d",
  );
});

test("only the first valid Euler substep reuses a completed forward pass", () => {
  const calls = [];
  const engine = Object.fromEntries(
    ["mj_forward", "mj_step", "critic_step_after_forward"].map((name) => [
      name,
      () => calls.push(name),
    ]),
  );
  const fast = bodyStepping(engine),
    m = { opt: { timestep: 0.0002, integrator: 0 } },
    d = {};
  fast.mj_forward(m, d);
  m.opt.timestep = 0.00005; // The real runtime's first step: must fully recompute.
  fast.mj_step(m, d);
  assert.deepEqual(calls.splice(0), ["mj_forward", "mj_step"]);
  fast.mj_forward(m, d);
  fast.mj_step(m, d);
  assert.equal(
    fast.mj_step,
    engine.mj_step,
    "remaining substeps call the engine directly",
  );
  fast.mj_step(m, d);
  assert.deepEqual(calls.splice(0), [
    "mj_forward",
    "critic_step_after_forward",
    "mj_step",
  ]);
  fast.mj_forward(m, d);
  fast.mj_step(m, {});
  assert.deepEqual(calls.splice(0), ["mj_forward", "mj_step"]);
  fast.mj_forward(m, d);
  m.opt.integrator = 1; // RK4 must not silently become Euler through step2.
  fast.mj_step(m, d);
  assert.deepEqual(calls.splice(0), ["mj_forward", "mj_step"]);
  m.opt.integrator = 0;
  engine.mj_forward = () => {
    throw new Error("Failed forward pass");
  };
  assert.throws(() => fast.mj_forward(m, d), /Failed forward/);
  fast.mj_step(m, d);
  assert.deepEqual(calls, ["mj_step"]);
});

test("cached stages reproduce full physics and observations across control changes", async () => {
  const { assets, policies } = await loadBodyAssets();
  const mj = await loadCurrent({
    wasmBinary: await fs.readFile(
      new URL("../static/vendor/mujoco-body-v2/mujoco.wasm", import.meta.url),
    ),
  });
  const bodies = [mj, bodyStepping(mj)].map(
    (engine) => new BodyRuntime(engine, assets, policies),
  );
  try {
    for (let i = 0; i < 700; i++) {
      const t = bodies[0].time;
      const command = {
        speed: t < 0.5 ? 2 : 20,
        turn: t > 0.7 ? 0.3 : 0,
        state: t < 0.5 ? "walking" : t < 1.1 ? "takeoff" : "flight",
        height: 1,
      };
      for (const b of bodies) b.step(command);
      const [a, b] = bodies;
      for (const key of [
        "qpos",
        "qvel",
        "act",
        "ctrl",
        "qacc",
        "qacc_warmstart",
        "sensordata",
        "efc_force",
      ])
        assert.deepEqual(b.d[key], a.d[key], `${key} at step ${i}`);
      assert.deepEqual(b.sensors, a.sensors);
      const counters = bodies.map((body) => {
        const timer = body.d.timer.get(0);
        try {
          return timer.number;
        } finally {
          timer.delete();
        }
      });
      assert.equal(
        counters[1],
        counters[0],
        "one counted integration per substep",
      );
      assert.deepEqual(b.snapshot(), a.snapshot());
      for (const kind of ["walking", "flight"])
        assert.deepEqual(
          b.observation(kind, 2, 0.3, 1, 0),
          a.observation(kind, 2, 0.3, 1, 0),
        );
    }
  } finally {
    for (const b of bodies) b.dispose();
  }
});

test("a numerical auto-reset invalidates cached physics stages", async () => {
  const { assets, policies } = await loadBodyAssets();
  const mj = await loadCurrent({
    wasmBinary: await fs.readFile(
      new URL("../static/vendor/mujoco-body-v2/mujoco.wasm", import.meta.url),
    ),
  });
  for (const key of ["qpos", "qvel"]) {
    const bodies = [0, 1].map(() => new BodyRuntime(mj, assets, policies));
    try {
      for (const b of bodies) b.d[key][0] = NaN;
      mj.mj_step(bodies[0].m, bodies[0].d);
      mj.critic_step_after_forward(bodies[1].m, bodies[1].d);
      for (const field of ["qpos", "qvel", "act", "sensordata"]) {
        assert.deepEqual(bodies[1].d[field], bodies[0].d[field], field);
        assert.ok(bodies[1].d[field].every(Number.isFinite), field);
      }
    } finally {
      for (const b of bodies) b.dispose();
    }
  }
});

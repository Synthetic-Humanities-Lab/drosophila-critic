import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { NeuralBodyAdapter, BodySupervisor } from "../static/body-adapter.js";
import { WorkerSession } from "../static/worker-session.js";
const config = JSON.parse(
  fs.readFileSync("static/assets/body-v1/adapter.json"),
);
const zero = () =>
  Object.fromEntries(
    [
      "walk",
      "turn_left",
      "turn_right",
      "takeoff",
      "flight",
      "flight_left",
      "flight_right",
    ].map((k) => ["motor_" + k, 0]),
  );

test("browser motor adapter matches Python over stimulation, release and repeated takeoffs", () => {
  const fixture = JSON.parse(
    fs.readFileSync("tests/fixtures/body-adapter.json"),
  );
  const adapter = new NeuralBodyAdapter(config);
  for (const { rates, command } of fixture) {
    const actual = adapter.step(rates);
    for (const key in command) {
      if (typeof command[key] === "boolean")
        assert.equal(actual[key], command[key]);
      else
        assert.ok(
          Math.abs(actual[key] - command[key]) < 1e-12,
          `${key}: ${actual[key]} vs ${command[key]}`,
        );
    }
  }
});

test("zero activity can never launch a body; arena corrections are separate events", () => {
  const adapter = new NeuralBodyAdapter(config),
    supervisor = new BodySupervisor(config);
  for (let i = 0; i < 100; i++)
    assert.equal(
      supervisor.command(adapter.step(zero()), {
        time: i * 0.02,
        dt: 0.02,
        position: [0, 0, 0.13],
        yaw: 0,
      }).state,
      "standing",
    );
  const neural = { ...adapter.step(zero()), walk_speed: 3 };
  const c = supervisor.command(neural, {
    time: 3,
    dt: 0.02,
    position: [8, 0, 0.13],
    yaw: 0,
  });
  assert.ok(c.boundary);
  assert.equal(c.requested.speed, 3);
  assert.notEqual(c.speed, 3);
  assert.equal(supervisor.events.at(-1).source, "arena confinement");
});

test("late messages from a cancelled worker cannot complete a replacement request", async () => {
  const old = globalThis.Worker,
    workers = [];
  globalThis.Worker = class {
    constructor() {
      workers.push(this);
    }
    postMessage() {}
    terminate() {
      this.stopped = true;
    }
  };
  try {
    const session = new WorkerSession("test", () => {});
    const first = session.request({ type: "simulate" });
    const cancelled = assert.rejects(first, { name: "AbortError" });
    session.cancel();
    await cancelled;
    const second = session.request({ type: "simulate" });
    workers[0].onmessage({ data: { type: "result", value: "stale" } });
    workers[1].onmessage({ data: { type: "result", value: "fresh" } });
    assert.equal((await second).value, "fresh");
    session.cancel();
    assert.ok(workers.every((w) => w.stopped));
  } finally {
    globalThis.Worker = old;
  }
});

import { NeuralBodyAdapter, BodySupervisor } from "./body-adapter.js";
import { BodyRuntime } from "./body-runtime.js";
import { bodyMetrics } from "./body-metrics.js";

export async function simulateBody(
  runtime,
  config,
  run,
  {
    baseline = 1.5,
    duration,
    onProgress = () => {},
    cancelled = () => false,
  } = {},
) {
  const { mj, assets, policies } = runtime,
    body = new BodyRuntime(mj, assets, policies);
  const adapter = new NeuralBodyAdapter(config),
    supervisor = new BodySupervisor(config);
  const motor = Object.keys(adapter.r).map((key) => {
    const i = run.group_names.indexOf(key);
    if (i < 0 || !run.group_sizes[i])
      throw new Error(`Missing full-spike motor capture: ${key}`);
    return [key, i, run.group_sizes[i]];
  });
  const frames = [],
    commands = [],
    inverted = [],
    started = performance.now();
  let invertedFor = 0;
  try {
    for (let frame = 0; frame < run.group_counts.length; frame++) {
      if (cancelled())
        throw new DOMException("Body processing cancelled.", "AbortError");
      const input = Object.fromEntries(
        motor.map(([k, i, n]) => [k, run.group_counts[frame][i] / n / 0.02]),
      );
      const command = adapter.step(input);
      const recordedCommand = { ...command };
      let applied,
        boundary = false;
      while (body.time < (frame + 1) * 0.02 - 1e-8) {
        applied = supervisor.command(command, {
          time: body.time,
          dt: ["takeoff", "flight", "landing"].includes(supervisor.state)
            ? 0.0002
            : 0.002,
          position: body.position,
          yaw: body.yaw,
          landed: body.landed,
        });
        boundary ||= applied.boundary;
        body.step(applied);
        command.takeoff = false;
      }
      const snapshot = body.snapshot(),
        p = body.position;
      if (Math.abs(p[0]) > 10 || Math.abs(p[1]) > 8 || p[2] > 10 || p[2] < 0)
        throw new Error(
          "The body left the tested arena. This run cannot be replayed as a valid movement result.",
        );
      inverted.push(body.d.xmat[body.root * 9 + 8] < 0);
      if (inverted.at(-1)) {
        invertedFor += 0.02;
      } else invertedFor = 0;
      if (invertedFor > 0.25)
        throw new Error(
          "The body controller lost its balance. This movement run failed; no substitute animation has been used.",
        );
      frames.push(snapshot);
      commands.push({
        ...recordedCommand,
        state: applied.state,
        speed: applied.speed,
        turn: applied.turn,
        body_reference_speed: body.commandSpeed,
        body_reference_turn: body.commandTurn,
        boundary,
      });
      if (frame % 25 === 0) {
        onProgress({
          fraction: frame / run.group_counts.length,
          simulated_seconds: body.time,
        });
        await new Promise((resolve) => setTimeout(resolve, 0));
      }
    }
    const result = {
      schema_version: "fly-body-playback-v1",
      root_index: body.root,
      time: frames.map((f) => Math.round((f.time - baseline) * 1e6) / 1e6),
      body_names: assets.model.bodies,
      positions: frames.map((f) => f.positions),
      quaternions: frames.map((f) => f.quaternions),
      states: frames.map((f) => f.state),
      airborne: frames.map((f) => f.airborne),
      commands,
      inverted,
      events: [...supervisor.events, ...body.events]
        .map((e) => ({
          ...e,
          time: Math.round((e.time - baseline) * 1e6) / 1e6,
        }))
        .sort((a, b) => a.time - b.time),
      provenance: {
        adapter: config,
        body: assets.model,
        seed: run.seed,
        runtime:
          "Official single-threaded MuJoCo 3.14.0 WebAssembly; frozen SavedModel mean policies",
        feedback:
          "Body sensors feed only the body policies; sound field is imposed.",
      },
    };
    result.metrics = {
      ...bodyMetrics(result, body.root, baseline, duration),
      wall_seconds: (performance.now() - started) / 1000,
    };
    return result;
  } finally {
    body.dispose();
  }
}

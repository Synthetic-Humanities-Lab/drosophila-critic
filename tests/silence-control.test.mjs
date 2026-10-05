import test from "node:test";
import assert from "node:assert/strict";
import { NeuralCapture } from "../static/neural-capture.js";
import {
  BODY_FRAME_KEYS,
  silencePrefix,
  loadSilenceControl,
} from "../static/silence-control.js";
import { stableJSON } from "../static/simulation-contract.js";
import { sha256 } from "../static/content-hash.js";

const contract = { baseline_steps: 0, configuration: { dt: 0.02 } };
function fixture() {
  const manifest = {
    version: "test",
    steps: 10,
    contract,
    neural: {
      seed: 1101,
      group_names: ["motor"],
      group_sizes: [1],
      spatial: {
        neuron_indices: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        bin_seconds: 0.1,
      },
    },
    body: { root_index: 0, events: [{ time: 0.06 }, { time: 0.2 }] },
  };
  const body = {
    time: Array.from({ length: 10 }, (_, i) => (i + 1) * 0.02),
    positions: Array.from({ length: 10 }, (_, i) => [[i, 0, 0]]),
    quaternions: Array.from({ length: 10 }, () => [[1, 0, 0, 0]]),
    states: Array(10).fill("walking"),
    airborne: Array(10).fill(false),
    commands: Array.from({ length: 10 }, (_, i) => ({ boundary: i > 5 })),
    inverted: Array.from({ length: 10 }, (_, i) => i === 2),
  };
  const chunks = [0, 5].map((start) => ({
    start,
    counts: [1, 1, 1, 1, 1],
    group_counts: [[1], [1], [1], [1], [1]],
    firing_steps: Array.from({ length: 5 }, (_, i) => [start + i]),
    body: Object.fromEntries(
      BODY_FRAME_KEYS.map((key) => [key, body[key].slice(start, start + 5)]),
    ),
  }));
  return { manifest, chunks };
}

test("saved silence regenerates every final partial neural bin without including future spikes", () => {
  const { manifest, chunks } = fixture();
  for (let steps = 6; steps <= 10; steps++) {
    const capture = new NeuralCapture({
      neurons: 10,
      display_neurons: manifest.neural.spatial.neuron_indices,
      groups: { motor: [0] },
    });
    for (let i = 0; i < steps; i++) capture.step([i], i === steps - 1);
    const prefix = silencePrefix(manifest, chunks, steps, 0.06);
    assert.deepEqual(
      prefix.run.spatial.firing_bins,
      capture.result().spatial.firing_bins,
    );
    assert.equal(prefix.body.positions.length, steps);
    assert.deepEqual(
      prefix.body.events,
      steps === 10 ? [{ time: 0.06 }, { time: 0.2 }] : [{ time: 0.06 }],
    );
    assert.equal(prefix.run.simulated_seconds, steps * 0.02);
  }
});

test("movement is measured over the matched prefix and the exact end of sound", () => {
  const { manifest, chunks } = fixture();
  const a = silencePrefix(manifest, chunks, 7, 0.06).body.metrics;
  const b = silencePrefix(manifest, chunks, 7, 0.061).body.metrics;
  assert.equal(a.distance_walked_cm, 6);
  assert.equal(a.after_voice_distance_cm, 4);
  assert.equal(b.after_voice_distance_cm, 3);
  assert.equal(a.inverted_seconds, 0.02);
  assert.equal(a.boundary_seconds, 0.02);
});

test("incomplete, reordered and out-of-range silence cannot become a comparison", () => {
  const { manifest, chunks } = fixture();
  assert.throws(() => silencePrefix(manifest, chunks, 11, 1), /cover/);
  assert.throws(
    () => silencePrefix(manifest, chunks.slice(0, 1), 7, 1),
    /incomplete/,
  );
  assert.throws(
    () => silencePrefix(manifest, chunks.toReversed(), 7, 1),
    /order/,
  );
  chunks[0].body.positions.pop();
  assert.throws(() => silencePrefix(manifest, chunks, 7, 1), /Incomplete/);
});

test("model mismatch is rejected before loading control chunks", async (t) => {
  const original = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = original;
  });
  let requests = 0;
  globalThis.fetch = async () => {
    requests++;
    return new Response(
      JSON.stringify({
        schema_version: "saved-silence-v1",
        contract_sha256: "wrong",
      }),
    );
  };
  await assert.rejects(
    loadSilenceControl(contract, 7, 1),
    /different simulation/,
  );
  assert.equal(requests, 1);
});

test("corrupt chunks and cancellation are rejected", async (t) => {
  const original = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = original;
  });
  const manifest = {
    ...fixture().manifest,
    schema_version: "saved-silence-v1",
    contract_sha256: await sha256(
      new TextEncoder().encode(stableJSON(contract)),
    ),
    chunks: [{ start: 0, file: "part.json.gz", sha256: "incorrect" }],
  };
  globalThis.fetch = async (url) =>
    new Response(
      url.pathname.endsWith("manifest.json")
        ? JSON.stringify(manifest)
        : "bad bytes",
    );
  await assert.rejects(loadSilenceControl(contract, 7, 1), /checksum/);
  const abort = new AbortController();
  abort.abort();
  await assert.rejects(
    loadSilenceControl(contract, 7, 1, { signal: abort.signal }),
    { name: "AbortError" },
  );
});

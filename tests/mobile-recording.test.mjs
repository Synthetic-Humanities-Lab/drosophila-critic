import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  conserveMemory,
  localSupport,
  LocalSession,
} from "../static/local-session.js";
import { RecordingPanel, recorderOptions } from "../static/recording-panel.js";
import { BrowserBrain } from "../static/browser-brain.js";
import { GROUP_IDS } from "../static/playback-data.js";

const model = JSON.parse(
  await readFile(
    new URL("../static/browser-model-v1/manifest.json", import.meta.url),
  ),
);

test("mobile capability checks allow iPhone and iPad without weakening required APIs", () => {
  const capable = {
    isSecureContext: true,
    Worker: class {},
    DecompressionStream: class {},
    WebAssembly: {},
    crypto: { subtle: {} },
    AudioContext: class {},
    OfflineAudioContext: class {},
  };
  for (const navigator of [
    { userAgent: "iPhone Mobile Safari" },
    { userAgent: "Safari", platform: "MacIntel", maxTouchPoints: 5 },
    { userAgent: "Android Chrome" },
    { userAgent: "Desktop", deviceMemory: 4 },
  ]) {
    assert.equal(localSupport({ ...capable, navigator }), null);
    assert.equal(conserveMemory({ navigator }), true);
  }
  assert.equal(
    conserveMemory({ navigator: { userAgent: "Desktop", deviceMemory: 8 } }),
    false,
  );
  for (const key of Object.keys(capable))
    assert.match(
      localSupport({ ...capable, [key]: undefined }),
      /missing a feature/,
    );
});

test("recording format selection supports newer and older Safari and browser defaults", () => {
  assert.deepEqual(recorderOptions({ isTypeSupported: () => true }), {
    mimeType: "audio/webm;codecs=opus",
  });
  assert.deepEqual(
    recorderOptions({ isTypeSupported: (t) => t === "audio/mp4" }),
    { mimeType: "audio/mp4" },
  );
  assert.deepEqual(recorderOptions({ isTypeSupported: () => false }), {});
  assert.deepEqual(recorderOptions({}), {});
});

test("a screen wake lock granted after cancellation is released immediately", async (t) => {
  const original = Object.getOwnPropertyDescriptor(globalThis, "navigator");
  t.after(() => {
    if (original) Object.defineProperty(globalThis, "navigator", original);
    else delete globalThis.navigator;
  });
  let grant,
    released = false;
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: {
      wakeLock: {
        request: () =>
          new Promise((resolve) => {
            grant = resolve;
          }),
      },
    },
  });
  const panel = Object.assign(Object.create(RecordingPanel.prototype), {
    busy: true,
    generation: 1,
  });
  const pending = panel.keepAwake(1);
  panel.generation++;
  panel.busy = false;
  grant({
    async release() {
      released = true;
    },
  });
  await pending;
  assert.equal(released, true);
  assert.equal(panel.wakeLock, undefined);
});

test("preparing a stopped recording decodes at 48 kHz without resuming playback", async (t) => {
  const original = globalThis.OfflineAudioContext;
  t.after(() => {
    globalThis.OfflineAudioContext = original;
  });
  globalThis.OfflineAudioContext = class {
    constructor(...args) {
      assert.deepEqual(args, [1, 1, 48000]);
    }
    async decodeAudioData() {
      return {
        sampleRate: 48000,
        duration: 1,
        length: 48000,
        numberOfChannels: 1,
        getChannelData: () => new Float32Array(48000).fill(0.25),
      };
    }
  };
  const elements = new Map();
  let preview;
  const panel = Object.assign(Object.create(RecordingPanel.prototype), {
    generation: 0,
    preview: {
      pause() {},
      setRecording(value) {
        preview = value;
      },
    },
    onStart() {},
    $(id) {
      if (!elements.has(id)) elements.set(id, { setAttribute() {} });
      return elements.get(id);
    },
  });
  await panel.prepare(new Blob(["fixture"]), "My reading.m4a");
  assert.equal(panel.draft.name, "My reading.m4a");
  assert.equal(panel.draft.samples.length, 48000);
  assert.equal(preview.duration, 1);
  assert.equal(panel.busy, false);
  assert.equal(panel.$("record-error").hidden, true);
});

test("reusing a brain resets its voltages, spikes and noise to a fresh seeded run", () => {
  const manifest = { ...model, neurons: 5, ear: [0] };
  const arrays = {
    indptr: new Uint32Array([0, 2, 3, 4, 5, 6]),
    indices: new Uint32Array([1, 2, 2, 3, 4, 0]),
    weights: new Float32Array([0.25, -0.1, 0.4, 0.2, 0.5, 0.3]),
  };
  const reused = new BrowserBrain(manifest, arrays);
  for (let i = 0; i < 80; i++) reused.step(0.8);
  reused.reset(1101);
  const fresh = new BrowserBrain(manifest, arrays);
  for (let i = 0; i < 80; i++) {
    assert.deepEqual(reused.step(i % 3 ? 0.2 : 0), fresh.step(i % 3 ? 0.2 : 0));
    assert.deepEqual(reused.v, fresh.v);
  }
});

function sessionFixture(
  sequential,
  { cancelAfterSound = false, failBody = false } = {},
) {
  const session = new LocalSession(() => {}, { sequential });
  session.model = model;
  session.display = { neuron_indices: [] };
  session.motor = { groups: {} };
  const events = [],
    neural = new Set(Object.values(session.neural));
  let neuralAlive = true;
  for (const worker of neural) {
    worker.cancel = () => {
      neuralAlive = false;
      events.push("release-neural");
    };
    worker.request = async ({ input, seed, label }) => {
      const condition = label.includes("silence") ? "silence" : "sound";
      events.push("neural-" + condition);
      if (cancelAfterSound && condition === "sound") session.cancel();
      return {
        seed,
        counts: input.map((x) => (x ? 2 : 1)),
        group_names: GROUP_IDS.slice(1),
        group_sizes: [1, 1, 1, 1],
        group_counts: input.map((x) => [x ? 1 : 0, 1, 0, 0]),
        spatial: { firing_bins: [], neuron_indices: [] },
      };
    };
  }
  for (const worker of new Set(Object.values(session.bodies))) {
    worker.initialize = async () => {
      assert.equal(
        neuralAlive,
        false,
        "neural heaps must be released before body initialization",
      );
      events.push("initialize-body");
    };
    worker.simulate = async (run, duration, label) => {
      events.push("body-" + (label.includes("silence") ? "silence" : "sound"));
      if (failBody) throw new Error("Body failed");
      return { duration, positions: run.counts, seed: run.seed };
    };
    worker.cancel = () => {
      events.push("release-body");
    };
  }
  return { session, events };
}

test("sequential scheduling retains both conditions and gives the parallel comparison's outputs", async () => {
  const samples = Float64Array.from(
    { length: 48000 },
    (_, i) => 0.1 * Math.sin(i / 30),
  );
  const a = sessionFixture(true),
    b = sessionFixture(false);
  assert.equal(a.session.neural.sound, a.session.neural.silence);
  assert.equal(a.session.bodies.sound, a.session.bodies.silence);
  assert.notEqual(b.session.neural.sound, b.session.neural.silence);
  const sequential = await a.session.process(samples, "source");
  const parallel = await b.session.process(samples, "source");
  for (const key of ["playback", "spatial", "body", "samples"])
    assert.deepEqual(sequential[key], parallel[key]);
  assert.equal(sequential.evidence.processing.execution, "sequential");
  assert.equal(parallel.evidence.processing.execution, "parallel");
  assert.deepEqual(
    a.events.filter((e) => e.startsWith("neural-") || e.startsWith("body-")),
    ["neural-sound", "neural-silence", "body-sound", "body-silence"],
  );
  assert.equal(a.session.model, null);
  assert.equal(a.session.busy, false);
});

test("cancellation between phone conditions does not start silence or body calculations", async () => {
  const { session, events } = sessionFixture(true, { cancelAfterSound: true });
  await assert.rejects(session.process(new Float64Array(48000), "source"), {
    name: "AbortError",
  });
  assert.equal(events.includes("neural-silence"), false);
  assert.equal(events.includes("initialize-body"), false);
  assert.equal(session.busy, false);
});

test("body failures release both model stages and leave the session retryable", async () => {
  const { session, events } = sessionFixture(true, { failBody: true });
  await assert.rejects(
    session.process(new Float64Array(48000), "source"),
    /Body failed/,
  );
  assert.ok(events.includes("release-body"));
  assert.equal(session.model, null);
  assert.equal(session.busy, false);
});

import test from "node:test";
import assert from "node:assert/strict";
import { NeuralCapture } from "../static/neural-capture.js";
import {
  normalizeRecording,
  mechanicalEncoding,
  mechanicalInput,
  mono,
} from "../static/local-audio.js";
import {
  GROUP_IDS,
  visitorPlayback,
  responseExplanation,
} from "../static/playback-data.js";
import { RecordedAudio } from "../static/audio-player.js";
import { LocalSession, localSupport } from "../static/local-session.js";
import { RecordingPanel, pcmWav } from "../static/recording-panel.js";

test("a cancelled microphone's late stop event cannot stop its replacement", async () => {
  const originalNavigator = Object.getOwnPropertyDescriptor(
    globalThis,
    "navigator",
  );
  const originalRecorder = globalThis.MediaRecorder;
  const streams = [];
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: {
      mediaDevices: {
        getUserMedia: async () => {
          const track = {
            stopped: false,
            stop() {
              this.stopped = true;
            },
          };
          const stream = { getTracks: () => [track] };
          streams.push(track);
          return stream;
        },
      },
    },
  });
  globalThis.MediaRecorder = class {
    start() {
      this.state = "recording";
    }
    stop() {
      this.state = "inactive";
    }
  };
  const elements = new Map();
  const panel = Object.assign(Object.create(RecordingPanel.prototype), {
    generation: 0,
    preview: { pause() {} },
    session: { cancel() {} },
    onStart() {},
    $(id) {
      if (!elements.has(id)) elements.set(id, { setAttribute() {} });
      return elements.get(id);
    },
  });
  try {
    await panel.record();
    const oldRecorder = panel.recorder;
    panel.cancel();
    await panel.record();
    oldRecorder.onstop();
    assert.equal(streams[0].stopped, true);
    assert.equal(streams[1].stopped, false);
    assert.equal(panel.recorder.state, "recording");
    assert.equal(panel.busy, true);
  } finally {
    panel.cancel();
    if (originalNavigator)
      Object.defineProperty(globalThis, "navigator", originalNavigator);
    else delete globalThis.navigator;
    if (originalRecorder) globalThis.MediaRecorder = originalRecorder;
    else delete globalThis.MediaRecorder;
  }
});

test("processed audio export retains PCM16 samples and declares its rate and length", async () => {
  const samples = Float64Array.from([0, 1 / 32768, -1, 32767 / 32768]);
  const buffer = await pcmWav(samples).arrayBuffer();
  const view = new DataView(buffer);
  assert.equal(buffer.byteLength, 52);
  assert.equal(view.getUint32(24, true), 48000);
  assert.equal(view.getUint32(40, true), 8);
  assert.deepEqual(
    Array.from({ length: 4 }, (_, i) => view.getInt16(44 + i * 2, true)),
    [0, 1, -32768, 32767],
  );
});

test("spatial capture records real sampled spikes, deduplicates a bin, and includes its final partial bin", () => {
  const m = {
    neurons: 8,
    groups: { input: [0, 1], other: [1, 4] },
    display_neurons: [0, 4, 7],
  };
  const capture = new NeuralCapture(m);
  for (const row of [[1, 4], [4], [0], [], [7], [1]]) capture.step(row);
  capture.step([4], true);
  const result = capture.result();
  assert.deepEqual(result.spatial.firing_bins, [[0, 1, 2], [1]]);
  assert.deepEqual(result.group_counts[0], [1, 2]);
  assert.deepEqual(result.group_counts[1], [0, 1]);
  assert.deepEqual(new NeuralCapture(m).result().spatial.firing_bins, []);
});
test("visitor normalization preserves silence and internal dynamics without a robot dependency", () => {
  const silent = normalizeRecording(new Float64Array(100));
  assert.ok(silent.metadata.silent);
  assert.equal(silent.metadata.gain, 1);
  assert.ok(silent.samples.every((x) => x === 0));
  const a = normalizeRecording(Float64Array.from([0, 0.1, -0.2, 0.4]));
  assert.equal(a.samples[0], 0);
  assert.ok(Math.abs(a.samples[1] * 4 - a.samples[3]) < 0.0001);
  assert.ok(Math.max(...a.samples.map(Math.abs)) <= 0.95);
  assert.equal(a.metadata.sample_count, a.samples.length);
  assert.equal(a.metadata.output_peak, Math.max(...a.samples.map(Math.abs)));
  assert.throws(() => normalizeRecording([NaN]), /range/);
  assert.throws(() => normalizeRecording([]), /empty/);
});

test("audio validation rejects oversized duration, incompatible rates and invalid playback clocks", () => {
  assert.throws(() => mono({ sampleRate: 48000, duration: 61 }), /60 seconds/);
  assert.throws(() => mono({ sampleRate: 44100, duration: 2 }), /48 kHz/);
  assert.throws(
    () => new RecordedAudio().setRecording({ duration: NaN }),
    /positive/,
  );
  const supported = {
    isSecureContext: true,
    Worker: class {},
    DecompressionStream: class {},
    AudioContext: class {},
    OfflineAudioContext: class {},
    WebAssembly: {},
    crypto: { subtle: {} },
    navigator: {
      userAgent: "Desktop",
      platform: "MacIntel",
      maxTouchPoints: 0,
    },
  };
  assert.equal(localSupport(supported), null);
  assert.equal(
    localSupport({
      ...supported,
      navigator: { ...supported.navigator, maxTouchPoints: 5 },
    }),
    null,
  );
  assert.match(
    localSupport({ ...supported, isSecureContext: false }),
    /missing a feature/,
  );
});

test("cancel stops a worker, rejects its request, and leaves no reusable stale model", async () => {
  const session = new LocalSession(() => {});
  let terminated = 0,
    aborted = false;
  const workers = [
    ...Object.values(session.neural),
    ...Object.values(session.bodies),
  ];
  for (const worker of workers)
    worker.worker = {
      postMessage() {},
      terminate() {
        terminated++;
      },
    };
  session.abort = {
    abort() {
      aborted = true;
    },
  };
  session.model = {};
  const rejection = Promise.all(
    workers.map((worker) =>
      assert.rejects(worker.request({ type: "simulate" }), {
        name: "AbortError",
      }),
    ),
  );
  session.cancel();
  await rejection;
  assert.equal(terminated, 4);
  assert.ok(aborted);
  assert.equal(session.model, null);
  for (const worker of workers) {
    assert.equal(worker.worker, null);
    assert.equal(worker.pending, null);
  }
});

test("a model initialization error terminates the failed worker before a retry", async () => {
  const originalFetch = globalThis.fetch,
    originalWorker = globalThis.Worker;
  const workers = [];
  globalThis.fetch = async () => ({
    ok: true,
    json: async () => ({ display_neurons: [], neuron_indices: [] }),
  });
  globalThis.Worker = class {
    constructor() {
      workers.push(this);
    }
    terminate() {
      this.terminated = true;
    }
    postMessage() {
      queueMicrotask(() =>
        this.onmessage({
          data: { type: "error", message: "Checksum mismatch" },
        }),
      );
    }
  };
  try {
    const session = new LocalSession(() => {});
    await assert.rejects(session.initialize(0), /Checksum mismatch/);
    assert.ok(workers[0].terminated);
    assert.equal(session.neural.sound.worker, null);
    await assert.rejects(session.initialize(0), /Checksum mismatch/);
    assert.equal(workers.length, 2);
    assert.ok(workers[1].terminated);
  } finally {
    globalThis.fetch = originalFetch;
    globalThis.Worker = originalWorker;
  }
});
test("mechanical visualization reports the same measured envelope that generates input", () => {
  const config = {
    frame_samples: 2,
    sample_rate: 100,
    decay_frames: 1,
    transition: [
      [1, 0],
      [0, 1],
    ],
    forcing: [1, 0],
    air_velocity_gain: 1,
    reference_nm: 1,
    cap: 0.8,
  };
  const record = mechanicalEncoding([1, 0, 0, 0], config);
  assert.deepEqual(record.injection, mechanicalInput([1, 0, 0, 0], config));
  assert.equal(record.frame_seconds, 0.02);
  assert.deepEqual(record.displacement_nm, [Math.sqrt(0.5), 1, 1]);
  assert.deepEqual(record.waveform_rms, [Math.sqrt(0.5), 0, 0]);
});
test("visitor metrics use named populations and subtract the paired silence without mislabeling raw firing", () => {
  const model = { neurons: 10 };
  const names = GROUP_IDS.slice(1).reverse();
  const run = (value) => ({
    seed: 1101,
    counts: Array(130).fill(value),
    group_names: names,
    group_sizes: [1, 1, 1, 1],
    group_counts: Array.from({ length: 130 }, () => [value, 0, 0, value]),
  });
  const input = { frame_seconds: 0.02, injection: Array(55).fill(0) };
  const record = visitorPlayback(run(2), run(1), model, 1, input, {});
  assert.equal(record.activity.sound.mean[0][0], 10);
  assert.equal(record.activity.silence.mean[0][0], 5);
  assert.equal(record.summary[0].change.mean, 5);
  assert.equal(record.summary[1].sound.mean, 100);
  assert.equal(record.summary[2].sound.mean, 0);
  assert.match(responseExplanation(record.summary[0], 1), /one simulation/);
  const identical = visitorPlayback(run(2), run(2), model, 1, input, {});
  assert.ok(
    identical.activity.change.mean.every((row) => row.every((x) => x === 0)),
  );
  assert.match(
    responseExplanation(identical.summary[0], 1),
    /same as in silence/,
  );
});
test("silence and the post-sound period share the audio clock and pause normally", async () => {
  class Context {
    currentTime = 0;
    destination = {};
    async resume() {}
    createBuffer(channels, length, rate) {
      return { duration: length / rate, copyToChannel() {} };
    }
    createBufferSource() {
      return { connect() {}, disconnect() {}, stop() {}, start() {} };
    }
  }
  const audio = new RecordedAudio();
  audio.context = new Context();
  audio.setRecording({
    samples: Float32Array.from([0.1, 0.2]),
    sampleRate: 2,
    duration: 4,
  });
  await audio.play();
  assert.equal(audio.buffer.duration, 4);
  audio.context.currentTime = 2;
  audio.pause();
  assert.equal(audio.currentTime, 2);
  audio.setRecording({ silent: true, duration: 4 });
  await audio.play();
  audio.context.currentTime = 5;
  assert.equal(audio.currentTime, 3);
});

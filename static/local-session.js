import { normalizeRecording, mechanicalEncoding } from "./local-audio.js";
import { visitorPlayback } from "./playback-data.js";
import { BodySession } from "./body-session.js";
import { WorkerSession } from "./worker-session.js";
import { sha256 } from "./content-hash.js";
import { loadSilenceControl } from "./silence-control.js";
import {
  simulationContract,
  stableJSON,
  BASELINE_STEPS,
  POST_STEPS,
  LOCAL_SEED,
} from "./simulation-contract.js";

export { sha256 } from "./content-hash.js";
async function json(url, signal) {
  const response = await fetch(url, { signal });
  if (!response.ok)
    throw new Error(
      `A model asset could not load (${response.status}). Try again.`,
    );
  return response.json();
}
export function localSupport(environment = globalThis) {
  if (
    !environment.isSecureContext ||
    !environment.Worker ||
    !environment.DecompressionStream ||
    !environment.WebAssembly ||
    !environment.crypto?.subtle ||
    !environment.AudioContext ||
    !environment.OfflineAudioContext
  )
    return "This browser is missing a feature needed for local processing. Try an up-to-date Safari or Chrome over HTTPS. The human, robot, and silence examples are still available.";
  return null;
}
export function conserveMemory(environment = globalThis) {
  const nav = environment.navigator || {};
  return (
    /Android|iPhone|iPad|Mobile/i.test(nav.userAgent || "") ||
    (nav.platform === "MacIntel" && nav.maxTouchPoints > 1) ||
    (nav.deviceMemory > 0 && nav.deviceMemory <= 4)
  );
}
export class LocalSession {
  constructor(
    onProgress,
    { sequential = conserveMemory(), savedSilence = true } = {},
  ) {
    this.onProgress = onProgress;
    this.sequential = sequential;
    this.savedSilence = savedSilence;
    this.neuralReady = new Set();
    this.generation = 0;
    const conditions = sequential ? ["sound"] : ["sound", "silence"];
    this.bodies = Object.fromEntries(
      conditions.map((key) => [key, new BodySession(onProgress)]),
    );
    this.neural = Object.fromEntries(
      conditions.map((key) => [
        key,
        new WorkerSession(
          new URL("./browser-benchmark.worker.js", import.meta.url),
          onProgress,
        ),
      ]),
    );
    if (sequential) {
      this.neural.silence = this.neural.sound;
      this.bodies.silence = this.bodies.sound;
    }
  }
  cancel() {
    this.generation++;
    this.abort?.abort();
    for (const worker of new Set([
      ...Object.values(this.neural),
      ...Object.values(this.bodies),
    ]))
      worker.cancel();
    this.model = null;
    this.neuralReady.clear();
  }
  async loadMetadata(token) {
    if (this.model) return;
    this.abort = new AbortController();
    const [model, display, motor, bodyManifest] = await Promise.all([
      json("./browser-model-v1/manifest.json", this.abort.signal),
      json(
        "./experiments/encounter-v2/display-neurons.json",
        this.abort.signal,
      ),
      json("./assets/body-v1/capture.json", this.abort.signal),
      json("./assets/body-v1/manifest.json", this.abort.signal),
    ]);
    if (token !== this.generation)
      throw new DOMException("Cancelled", "AbortError");
    if (
      JSON.stringify(model.display_neurons) !==
      JSON.stringify(display.neuron_indices)
    )
      throw new Error(
        "Neuron coordinates do not match this model. Reload the page.",
      );
    this.model = model;
    this.display = display;
    this.motor = motor;
    this.bodyManifest = bodyManifest;
  }
  async initialize(token, { soundOnly = false } = {}) {
    await this.loadMetadata(token);
    // Saved silence needs no second worker. Fresh fallback still resets both runs.
    const workers = soundOnly
      ? [this.neural.sound]
      : Object.values(this.neural);
    for (const worker of new Set(workers)) {
      if (token !== this.generation)
        throw new DOMException("Cancelled", "AbortError");
      if (this.neuralReady.has(worker)) continue;
      await worker.request({
        type: "initialize",
        url: "./browser-model-v1/manifest.json",
        cache: true,
        captureGroups: this.motor.groups,
      });
      this.neuralReady.add(worker);
    }
    if (token !== this.generation)
      throw new DOMException("Cancelled", "AbortError");
  }
  async process(samples, recordingHash) {
    if (this.busy) throw new Error("A recording is already being processed.");
    this.busy = true;
    const started = performance.now();
    const timing = { execution: this.sequential ? "sequential" : "parallel" };
    const token = ++this.generation;
    const check = () => {
      if (token !== this.generation)
        throw new DOMException("Cancelled", "AbortError");
    };
    try {
      await this.loadMetadata(token);
      check();
      this.onProgress({
        stage: "Translating sound into hearing input",
        fraction: 0,
      });
      const normalized = normalizeRecording(samples);
      const input = mechanicalEncoding(normalized.samples, this.model.receiver);
      const duration = samples.length / 48000;
      const contract = simulationContract(
        this.model,
        this.motor,
        this.bodyManifest,
      );
      const contractHash = await sha256(
        new TextEncoder().encode(stableJSON(contract)),
      );
      check();
      const steps = BASELINE_STEPS + input.injection.length + POST_STEPS;
      let control = null,
        controlError = null;
      const controlStarted = performance.now();
      if (this.savedSilence) {
        try {
          control = await loadSilenceControl(contract, steps, duration, {
            signal: this.abort?.signal,
            onProgress: this.onProgress,
          });
        } catch (error) {
          check();
          if (error.name === "AbortError") throw error;
          controlError = error.message;
          this.onProgress({
            stage:
              "Saved silence unavailable; calculating it on this device instead",
            fraction: 0,
          });
        }
      }
      check();
      timing.saved_control_seconds =
        (performance.now() - controlStarted) / 1000;
      timing.silence_reused = Boolean(control);
      if (control) timing.execution = "sound-only-with-saved-control";
      const loadStarted = performance.now();
      await this.initialize(token, { soundOnly: Boolean(control) });
      check();
      timing.model_load_seconds = (performance.now() - loadStarted) / 1000;
      const runs = {};
      if (control) runs.silence = control.run;
      const neuralStarted = performance.now();
      const simulateNeural = async (condition) => {
        check();
        const frames = [
          ...Array(BASELINE_STEPS).fill(0),
          ...(condition === "sound"
            ? input.injection
            : Array(input.injection.length).fill(0)),
          ...Array(POST_STEPS).fill(0),
        ];
        runs[condition] = await this.neural[condition].request({
          type: "simulate",
          input: frames,
          capture: true,
          seed: LOCAL_SEED,
          label:
            condition === "sound"
              ? "Listening to your recording"
              : "Running its silence control",
        });
      };
      if (control) await simulateNeural("sound");
      else if (this.sequential) {
        await simulateNeural("sound");
        await simulateNeural("silence");
      } else await Promise.all(["sound", "silence"].map(simulateNeural));
      check();
      timing.neural_pair_seconds = (performance.now() - neuralStarted) / 1000;
      // The body uses captured spikes, so the connectivity heaps can be released now.
      for (const worker of new Set(Object.values(this.neural))) worker.cancel();
      const playback = visitorPlayback(
        runs.sound,
        runs.silence,
        this.model,
        samples.length / 48000,
        input,
        normalized.metadata,
      );
      const body = {};
      if (control) body.silence = control.body;
      const bodyStarted = performance.now();
      await this.bodies.sound.initialize();
      check();
      if (!control) await this.bodies.silence.initialize();
      check();
      const simulateBody = async (condition) => {
        check();
        body[condition] = await this.bodies[condition].simulate(
          runs[condition],
          samples.length / 48000,
          condition === "sound"
            ? "Calculating movement · your voice"
            : "Calculating movement · silence",
        );
      };
      if (control) await simulateBody("sound");
      else if (this.sequential) {
        await simulateBody("sound");
        await simulateBody("silence");
      } else await Promise.all(["sound", "silence"].map(simulateBody));
      check();
      playback.body = {
        available: true,
        version: "listening-body-v1",
        seed: 1101,
      };
      timing.body_pair_seconds = (performance.now() - bodyStarted) / 1000;
      const processedHash = await sha256(normalized.samples.buffer);
      check();
      timing.total_seconds = (performance.now() - started) / 1000;
      const spatial = Object.fromEntries(
        Object.entries(runs).map(([condition, run]) => [
          condition,
          {
            ...this.display,
            ...run.spatial,
            condition,
            seed: 1101,
            start_time: -1.5,
          },
        ]),
      );
      const evidence = {
        schema_version: "local-listening-v4",
        contract_sha256: contractHash,
        silence_control: control?.provenance || {
          kind: "calculated-on-device",
          fallback_reason: controlError,
        },
        recording_sha256: recordingHash,
        audio: {
          sample_rate: 48000,
          duration: samples.length / 48000,
          processed_float64_sha256: processedHash,
          hash_format:
            "Contiguous Float64 PCM samples in this device's byte order",
          decoding:
            "Web Audio mono at 48 kHz; browser codec and microphone settings may differ",
        },
        model: this.model.version,
        receiver: this.model.receiver,
        seed: 1101,
        fly: {
          connectome: "MaleCNS v1.0",
          upstream_commit: this.model.upstream_commit,
          configuration: this.model.configuration,
          rng: "PCG64",
          array_sha256: Object.fromEntries(
            Object.entries(this.model.arrays).map(([k, v]) => [k, v.sha256]),
          ),
        },
        playback,
        spatial,
        body,
        motor_capture: this.motor,
        body_assets: this.bodies.sound.info,
        processing: timing,
        raw_runs: runs,
        limitations: [
          "One sound/silence pair, not a repeated result",
          "No transcription or line alignment",
          "Provisional mechanical-to-neural coupling",
          "Movement uses a declared engineering adapter and separate frozen body policies, not a validated biological prediction",
          "Browser decoding may differ from Python",
        ],
      };
      return { playback, spatial, body, samples: normalized.samples, evidence };
    } finally {
      // Also release heaps after an error. Cached model assets contain no audio.
      if (token === this.generation) this.cancel();
      this.busy = false;
    }
  }
}

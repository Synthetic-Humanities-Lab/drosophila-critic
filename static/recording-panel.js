import { RecordedAudio } from "./audio-player.js";
import { mono } from "./local-audio.js";
import { LocalSession, localSupport, sha256 } from "./local-session.js";
import { timeLabel } from "./playback-data.js";

export function saveFile(blob, name) {
  const url = URL.createObjectURL(blob),
    link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
export function pcmWav(samples) {
  const bytes = new ArrayBuffer(44 + samples.length * 2),
    view = new DataView(bytes);
  const word = (offset, text) =>
    [...text].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  word(0, "RIFF");
  view.setUint32(4, bytes.byteLength - 8, true);
  word(8, "WAVEfmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, 48000, true);
  view.setUint32(28, 96000, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  word(36, "data");
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((x, i) =>
    view.setInt16(
      44 + i * 2,
      Math.max(-32768, Math.min(32767, Math.round(x * 32768))),
      true,
    ),
  );
  return new Blob([bytes], { type: "audio/wav" });
}
export class RecordingPanel {
  constructor({ onResult, onStart }) {
    this.$ = (id) => document.getElementById(id);
    this.onResult = onResult;
    this.onStart = onStart;
    this.generation = 0;
    this.preview = new RecordedAudio();
    this.session = new LocalSession(({ stage, fraction }) => {
      this.$("record-status").textContent = stage;
      this.$("record-progress").value = fraction || 0;
      this.$("record-percent").textContent =
        `${Math.round((fraction || 0) * 100)}%`;
    });
    this.$("record-start").onclick = () => this.record();
    this.$("try-example").onclick = () => this.useExample();
    this.$("record-stop").onclick = () => this.recorder?.stop();
    this.$("voice-file").onchange = (e) => {
      const file = e.target.files[0];
      if (file) this.prepare(file, file.name);
      e.target.value = "";
    };
    this.$("preview-voice").onclick = async () => {
      this.onStart();
      try {
        if (this.preview.paused) await this.preview.play();
        else this.preview.pause();
        this.$("preview-voice").textContent = this.preview.paused
          ? "Listen back"
          : "Pause preview";
      } catch (e) {
        this.fail(e);
      }
    };
    this.preview.addEventListener("ended", () => {
      this.$("preview-voice").textContent = "Listen back";
    });
    this.$("process-voice").onclick = () => this.process();
    this.$("cancel-voice").onclick = () => this.cancel();
    this.$("clear-voice").onclick = () => {
      this.cancel();
      this.draft = null;
      this.preview.samples = null;
      this.preview.buffer = null;
      this.$("voice-preview").hidden = true;
    };
    this.$("download-result").onclick = () =>
      this.result &&
      saveFile(
        new Blob([JSON.stringify(this.result.evidence)], {
          type: "application/json",
        }),
        "fly-response.json",
      );
    this.$("download-processed").onclick = () =>
      this.result && saveFile(pcmWav(this.result.samples), "fly-input.wav");
    this.$("download-original").onclick = () =>
      this.original && saveFile(this.original.blob, this.original.name);
    const unsupported = localSupport();
    if (unsupported) {
      this.$("support-note").textContent = unsupported;
      this.$("record-inputs").hidden = true;
    }
    addEventListener("pagehide", () => {
      this.cancel();
      this.context?.close();
      this.context = null;
      this.preview.context?.close();
    });
  }
  setBusy(busy, recording = false) {
    this.busy = busy;
    for (const id of [
      "record-start",
      "try-example",
      "voice-file",
      "process-voice",
      "clear-voice",
      "preview-voice",
    ])
      this.$(id).disabled = busy;
    this.$("record-stop").hidden = !recording;
    this.$("cancel-voice").hidden = !busy;
    this.$("processing-progress").hidden = !busy || recording;
    this.$("record-inputs").setAttribute("aria-busy", String(busy));
  }
  stopTracks() {
    clearInterval(this.timer);
    clearTimeout(this.limit);
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
  }
  cancel() {
    this.generation++;
    this.session.cancel();
    this.preview.pause();
    if (this.recorder?.state === "recording") this.recorder.stop();
    this.stopTracks();
    this.setBusy(false);
    this.$("record-status").textContent =
      "Stopped. Your recording stays on this device.";
    this.$("preview-voice").textContent = "Listen back";
  }
  fail(error) {
    this.$("record-status").textContent =
      "Choose another recording or try again.";
    this.$("record-error").textContent =
      error.name === "NotAllowedError"
        ? "Microphone access was not granted. You can choose an audio file instead."
        : error.name === "NotFoundError"
          ? "No microphone was found. Choose an audio file instead."
          : error.name === "RangeError"
            ? "The browser ran out of memory. Close other tabs or play an example."
            : error.message ||
              "The recording could not be processed. Please try again.";
    this.$("record-error").hidden = false;
  }
  async useExample() {
    if (this.busy) return;
    const token = ++this.generation;
    this.setBusy(true);
    this.$("record-error").hidden = true;
    try {
      this.$("record-status").textContent = "Opening the public robot example…";
      const response = await fetch("./experiments/encounter-v1/a.wav");
      if (!response.ok)
        throw new Error("The public example is unavailable. Please retry.");
      const blob = await response.blob();
      if (token !== this.generation) return;
      this.setBusy(false);
      await this.prepare(blob, "Robot example.wav", true);
    } catch (error) {
      if (token === this.generation) {
        this.setBusy(false);
        this.fail(error);
      }
    }
  }
  async prepare(blob, name, example = false) {
    if (this.busy) return;
    const token = ++this.generation;
    this.setBusy(true);
    this.preview.pause();
    this.onStart();
    this.$("record-error").hidden = true;
    try {
      if (!blob.size || blob.size > 64000000)
        throw new Error("Choose a non-empty audio file smaller than 64 MB.");
      this.$("record-status").textContent =
        "Opening your recording on this device…";
      this.context ||= new AudioContext({ sampleRate: 48000 });
      await this.context.resume();
      const bytes = await blob.arrayBuffer();
      let decoded;
      try {
        decoded = await this.context.decodeAudioData(bytes.slice(0));
      } catch {
        throw new Error(
          "This file could not be decoded as audio. Try WAV, MP3, M4A, or a browser recording.",
        );
      }
      const samples = mono(decoded),
        hash = await sha256(bytes);
      if (token !== this.generation) return;
      this.draft = { blob, name, samples, hash, example };
      this.$("process-voice").textContent = "READ TO THE FLY →";
      this.$("preview-voice").textContent = "Listen back";
      this.preview.setRecording({ samples, duration: samples.length / 48000 });
      this.$("voice-preview").hidden = false;
      this.$("recording-name").textContent = name;
      this.$("recording-duration").textContent =
        `${(samples.length / 48000).toFixed(1)} seconds`;
      this.$("record-status").textContent = this.result
        ? "Listen back, then process this recording to replace the earlier response above."
        : "Listen back, replace it, or read it to the fly.";
    } catch (e) {
      if (token === this.generation) this.fail(e);
    } finally {
      if (token === this.generation) this.setBusy(false);
    }
  }
  async record() {
    if (this.busy) return;
    const token = ++this.generation;
    this.setBusy(true, true);
    this.preview.pause();
    this.onStart();
    this.$("record-error").hidden = true;
    try {
      if (!navigator.mediaDevices?.getUserMedia || !globalThis.MediaRecorder)
        throw new Error(
          "Recording is unavailable in this browser. Choose an audio file instead.",
        );
      this.$("record-status").textContent =
        "Waiting for microphone permission…";
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      });
      if (token !== this.generation) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      this.stream = stream;
      const recorder = new MediaRecorder(stream),
        chunks = [];
      this.recorder = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size) chunks.push(e.data);
      };
      recorder.onerror = () => {
        if (token === this.generation) {
          this.cancel();
          this.fail(
            new Error(
              "Microphone recording failed. Choose a file or try again.",
            ),
          );
        }
      };
      recorder.onstop = () => {
        if (token !== this.generation) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        this.stopTracks();
        this.setBusy(false);
        const ext = recorder.mimeType.includes("mp4")
          ? "m4a"
          : recorder.mimeType.includes("ogg")
            ? "ogg"
            : "webm";
        this.prepare(
          new Blob(chunks, { type: recorder.mimeType }),
          `My reading.${ext}`,
        );
      };
      recorder.start();
      const started = performance.now();
      this.$("record-status").textContent = "Recording · 0:00 / 0:59";
      this.timer = setInterval(() => {
        this.$("record-status").textContent =
          `Recording · ${timeLabel((performance.now() - started) / 1000)} / 0:59`;
      }, 200);
      this.limit = setTimeout(() => {
        if (recorder.state === "recording") recorder.stop();
      }, 59000);
    } catch (e) {
      if (token === this.generation) {
        this.stopTracks();
        this.setBusy(false);
        this.fail(e);
      }
    }
  }
  async process() {
    if (this.busy || !this.draft) return;
    const token = ++this.generation,
      draft = this.draft;
    this.setBusy(true);
    this.preview.pause();
    this.onStart();
    this.$("record-error").hidden = true;
    this.$("record-status").textContent =
      "Loading the fly model. Your audio stays here.";
    try {
      const result = await this.session.process(draft.samples, draft.hash);
      if (token !== this.generation) return;
      result.name = draft.name;
      result.example = draft.example;
      result.evidence.source = draft.example
        ? "Public robot example, processed locally"
        : "Visitor-selected recording";
      this.result = result;
      this.original = draft;
      this.$("voice-downloads").hidden = false;
      this.$("record-status").textContent =
        "Ready. Play your recording and watch its response above.";
      this.$("process-voice").textContent = "Process again";
      await this.onResult(result);
    } catch (e) {
      if (token === this.generation) {
        this.session.cancel();
        if (e.name !== "AbortError") this.fail(e);
      }
    } finally {
      if (token === this.generation) this.setBusy(false);
    }
  }
}

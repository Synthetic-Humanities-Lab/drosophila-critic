// AudioContext's clock drives both playback and the recorded neural trajectory.
export class RecordedAudio extends EventTarget {
  constructor() {
    super();
    this.context = null;
    this.buffer = null;
    this.source = null;
    this.generation = 0;
    this.playRequested = false;
    this.offset = 0;
    this.started = 0;
    this.paused = true;
    this.duration = 0;
    this.playbackEnd = null;
  }
  async load(url, { duration = 0 } = {}) {
    this.pause();
    this.generation++;
    this.offset = 0;
    this.buffer = null;
    this.bytes = null;
    const generation = this.generation;
    this.duration = duration;
    this.extendedDuration = duration;
    this.samples = null;
    this.silent = false;
    const response = await fetch(url);
    if (!response.ok)
      throw new Error("The saved waveform could not be loaded.");
    const bytes = await response.arrayBuffer();
    if (generation === this.generation) this.bytes = bytes;
  }
  setRecording({
    samples = null,
    sampleRate = 48000,
    duration,
    silent = false,
  }) {
    if (
      !Number.isFinite(duration) ||
      duration <= 0 ||
      !Number.isFinite(sampleRate) ||
      sampleRate <= 0
    )
      throw new Error("Audio duration and sample rate must be positive.");
    this.pause();
    this.generation++;
    this.offset = 0;
    this.buffer = null;
    this.bytes = null;
    this.samples = samples;
    this.sampleRate = sampleRate;
    this.extendedDuration = duration;
    this.duration = duration;
    this.silent = silent;
  }
  get currentTime() {
    return this.paused
      ? this.offset
      : Math.min(
          this.playbackEnd ?? this.duration,
          this.offset + this.context.currentTime - this.started,
        );
  }
  set currentTime(value) {
    const resume = !this.paused;
    this.pause();
    this.offset = Math.max(0, Math.min(this.duration, value));
    this.dispatchEvent(new Event("seeking"));
    if (resume) this.play().catch(() => this.dispatchEvent(new Event("error")));
  }
  async play(endTime = null) {
    if (!this.paused || this.playRequested) return;
    this.playRequested = true;
    const generation = this.generation;
    if (!this.context || this.context.state === "closed")
      this.context = new AudioContext();
    let buffer;
    try {
      await this.context.resume();
      if (this.buffer) buffer = this.buffer;
      else if (this.silent || this.samples) {
        const rate = this.sampleRate || 48000;
        buffer = this.context.createBuffer(
          1,
          Math.ceil(this.extendedDuration * rate),
          rate,
        );
        if (!this.silent && this.samples)
          buffer.copyToChannel(Float32Array.from(this.samples), 0);
      } else {
        buffer = await this.context.decodeAudioData(this.bytes.slice(0));
        if (this.extendedDuration > buffer.duration) {
          const padded = this.context.createBuffer(
            buffer.numberOfChannels,
            Math.ceil(this.extendedDuration * buffer.sampleRate),
            buffer.sampleRate,
          );
          for (let c = 0; c < buffer.numberOfChannels; c++)
            padded.copyToChannel(buffer.getChannelData(c), c);
          buffer = padded;
        }
      }
    } catch (error) {
      if (generation === this.generation) this.playRequested = false;
      throw error;
    }
    if (!this.playRequested || generation !== this.generation) return;
    this.buffer = buffer;
    this.duration = this.buffer.duration;
    if (this.offset >= this.duration) this.offset = 0;
    const end =
      endTime === null ? this.duration : Math.min(endTime, this.duration);
    if (!Number.isFinite(end) || end <= this.offset) {
      this.playRequested = false;
      throw new Error("The playback interval must end after its start.");
    }
    this.playbackEnd = end;
    this.source = this.context.createBufferSource();
    this.source.buffer = this.buffer;
    this.source.connect(this.context.destination);
    this.started = this.context.currentTime;
    this.paused = false;
    this.source.onended = () => {
      this.offset = end;
      this.playbackEnd = null;
      this.paused = true;
      this.playRequested = false;
      this.source = null;
      this.dispatchEvent(new Event("ended"));
    };
    this.source.start(0, this.offset, end - this.offset);
    this.dispatchEvent(new Event("play"));
  }
  pause() {
    this.playRequested = false;
    this.offset = this.currentTime;
    if (this.source) {
      this.source.onended = null;
      this.source.stop();
      this.source.disconnect();
      this.source = null;
    }
    this.paused = true;
    this.dispatchEvent(new Event("pause"));
  }
}

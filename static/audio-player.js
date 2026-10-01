// AudioContext's clock drives both playback and the recorded neural trajectory.
export class RecordedAudio extends EventTarget {
  constructor() {
    super();
    this.context = null; this.buffer = null; this.source = null;
    this.generation = 0; this.playRequested = false;
    this.offset = 0; this.started = 0; this.paused = true; this.duration = 0;
  }
  async load(url) {
    this.pause(); this.generation++; this.offset = 0; this.buffer = null; this.bytes = null;
    const generation = this.generation;
    this.duration = 0;
    const response = await fetch(url);
    if (!response.ok) throw new Error('The saved waveform could not be loaded.');
    const bytes = await response.arrayBuffer();
    if (generation === this.generation) this.bytes = bytes;
  }
  get currentTime() {
    return this.paused ? this.offset : Math.min(this.duration, this.offset + this.context.currentTime - this.started);
  }
  set currentTime(value) {
    const resume = !this.paused;
    this.pause(); this.offset = Math.max(0, Math.min(this.duration, value));
    this.dispatchEvent(new Event('seeking'));
    if (resume) this.play().catch(() => this.dispatchEvent(new Event('error')));
  }
  async play() {
    if (!this.paused || this.playRequested) return;
    this.playRequested = true;
    const generation = this.generation;
    if (!this.context) this.context = new AudioContext();
    let buffer;
    try {
      await this.context.resume();
      buffer = this.buffer || await this.context.decodeAudioData(this.bytes.slice(0));
    } catch (error) {
      if (generation === this.generation) this.playRequested = false;
      throw error;
    }
    if (!this.playRequested || generation !== this.generation) return;
    this.buffer = buffer;
    this.duration = this.buffer.duration;
    if (this.offset >= this.duration) this.offset = 0;
    this.source = this.context.createBufferSource();
    this.source.buffer = this.buffer;
    this.source.connect(this.context.destination);
    this.started = this.context.currentTime;
    this.paused = false;
    this.source.onended = () => {
      this.offset = this.duration; this.paused = true; this.playRequested = false; this.source = null;
      this.dispatchEvent(new Event('ended'));
    };
    this.source.start(0, this.offset);
    this.dispatchEvent(new Event('play'));
  }
  pause() {
    this.playRequested = false;
    this.offset = this.currentTime;
    if (this.source) {
      this.source.onended = null; this.source.stop(); this.source.disconnect(); this.source = null;
    }
    this.paused = true;
    this.dispatchEvent(new Event('pause'));
  }
}

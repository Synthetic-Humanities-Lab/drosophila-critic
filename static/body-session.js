import { WorkerSession } from "./worker-session.js";

export class BodySession extends WorkerSession {
  constructor(onProgress) {
    super(new URL("./body.worker.js", import.meta.url), onProgress);
  }
  async initialize() {
    if (this.ready) return;
    this.info = await this.request({ type: "initialize" });
    this.ready = true;
  }
  async simulate(run, duration, label) {
    await this.initialize();
    return (await this.request({ type: "simulate", run, duration, label }))
      .result;
  }
  cancel() {
    super.cancel();
    this.ready = false;
  }
}

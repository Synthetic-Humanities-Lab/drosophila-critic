// One request at a time per worker; separate conditions have separate state.
export class WorkerSession {
  constructor(url, onProgress) {
    this.url = url;
    this.onProgress = onProgress;
  }
  start() {
    if (this.worker) return;
    const worker = new Worker(this.url, { type: "module" });
    this.worker = worker;
    worker.onmessage = ({ data }) => {
      if (this.worker !== worker) return;
      if (data.type === "progress") {
        this.onProgress(data);
        return;
      }
      const pending = this.pending;
      this.pending = null;
      if (data.type === "cancelled") {
        this.cancel();
        pending?.reject(new DOMException(data.message, "AbortError"));
      } else if (data.type === "error") {
        this.cancel();
        pending?.reject(new Error(data.message));
      } else pending?.resolve(data);
    };
    worker.onerror = () => {
      const pending = this.pending;
      this.pending = null;
      this.cancel();
      pending?.reject(
        new Error(
          "The local model stopped unexpectedly. Your audio has not been uploaded.",
        ),
      );
    };
  }
  request(data) {
    this.start();
    if (this.pending)
      return Promise.reject(
        new Error("A calculation is already running in this worker."),
      );
    return new Promise((resolve, reject) => {
      this.pending = { resolve, reject };
      this.worker.postMessage(data);
    });
  }
  cancel() {
    this.worker?.terminate();
    this.worker = null;
    const pending = this.pending;
    this.pending = null;
    pending?.reject(new DOMException("Processing cancelled.", "AbortError"));
  }
}

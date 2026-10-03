import { LocalSession, sha256 } from "./local-session.js";
const $ = (id) => document.getElementById(id);
let result,
  running = false,
  started,
  cancelRequested,
  session;
$("start").onclick = async () => {
  if (running) return;
  running = true;
  result = null;
  $("save").disabled = true;
  $("start").disabled = true;
  $("cancel").disabled = false;
  $("report").textContent = "";
  started = performance.now();
  cancelRequested = null;
  session = new LocalSession((p) => {
    $("status").textContent = p.stage;
    $("progress").value = p.fraction || 0;
  });
  try {
    const response = await fetch("./experiments/encounter-v1/a.wav");
    if (!response.ok) throw new Error("Public audio fixture missing.");
    const ctx = new AudioContext({ sampleRate: 48000 }),
      buffer = await ctx.decodeAudioData(await response.arrayBuffer());
    const source = buffer.getChannelData(0),
      samples = new Float64Array(48000 * 60);
    for (let i = 0; i < samples.length; i++)
      samples[i] = source[i % source.length];
    await ctx.close();
    if (cancelRequested !== null)
      throw new DOMException("Cancelled", "AbortError");
    const run = await session.process(samples, await sha256(samples.buffer));
    result = {
      schema_version: "local-body-benchmark-v1",
      audio: "Public robot fixture repeated to 60 seconds; no new performance",
      duration: 60,
      environment: {
        user_agent: navigator.userAgent,
        hardware_concurrency: navigator.hardwareConcurrency,
        device_memory_gb: navigator.deviceMemory ?? null,
      },
      processing: run.evidence.processing,
      body_assets: run.evidence.body_assets,
      body: {},
      download_entries: performance.getEntriesByType("resource").map((r) => ({
        name: r.name,
        bytes: r.transferSize,
        duration_ms: r.duration,
      })),
      memory_note:
        "Body linear memory and policy buffers are measured; browser-wide peak memory is not exposed consistently by this API.",
    };
    for (const condition of ["sound", "silence"])
      result.body[condition] = {
        metrics: run.body[condition].metrics,
        pose_sha256: await sha256(
          new TextEncoder().encode(
            JSON.stringify(run.body[condition].positions),
          ),
        ),
      };
    result.passed =
      run.evidence.processing.total_seconds <= 300 &&
      Object.values(result.body).every((x) => x.metrics.complete);
    $("report").textContent = JSON.stringify(result, null, 2);
    $("status").textContent = result.passed
      ? "PASS · complete local processing within five minutes"
      : "FAIL · exceeded five minutes";
    $("save").disabled = false;
  } catch (e) {
    result = {
      passed: false,
      error: e.message,
      seconds: (performance.now() - started) / 1000,
      cancellation_latency_ms:
        cancelRequested === null ? null : performance.now() - cancelRequested,
    };
    $("report").textContent = JSON.stringify(result, null, 2);
    $("status").textContent = e.name === "AbortError" ? "Cancelled" : e.message;
    session.cancel();
    $("save").disabled = false;
  } finally {
    running = false;
    $("start").disabled = false;
    $("cancel").disabled = true;
  }
};
$("cancel").onclick = () => {
  cancelRequested = performance.now();
  session?.cancel();
};
$("save").onclick = () => {
  if (!result) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(
    new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }),
  );
  a.download = "fly-body-benchmark.json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 60000);
};
addEventListener("pagehide", () => session?.cancel());

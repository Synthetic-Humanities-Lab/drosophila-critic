import { mechanicalEncoding } from "./local-audio.js";

const $ = (id) => document.getElementById(id),
  worker = new Worker(
    new URL("./browser-benchmark.worker.js", import.meta.url),
    { type: "module" },
  );
const report = {
  browser: navigator.userAgent,
  hardware_threads: navigator.hardwareConcurrency,
  device_memory_gb: navigator.deviceMemory ?? null,
  results: [],
  visitor_recording_enabled: false,
};
let pending = null;
async function responseHashes(run) {
  const result = {};
  for (const [name, value] of Object.entries({
    counts: run.counts,
    groups: run.group_counts,
    spatial: run.spatial.firing_bins,
  })) {
    const bytes = await crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(JSON.stringify(value)),
    );
    result[name] = Array.from(new Uint8Array(bytes), (n) =>
      n.toString(16).padStart(2, "0"),
    ).join("");
  }
  return result;
}
function summary() {
  return {
    ...report,
    results: report.results.map(
      ({ counts, group_counts, spatial, ...rest }) => ({
        ...rest,
        recorded_steps: counts.length,
        captured_population_steps: group_counts?.length ?? 0,
        displayed_neurons: spatial?.neuron_indices.length ?? 0,
        captured_spatial_bins: spatial?.firing_bins.length ?? 0,
      }),
    ),
  };
}
const run = (data) =>
  new Promise((resolve, reject) => {
    pending = { resolve, reject };
    worker.postMessage(data);
  });
worker.onmessage = ({ data }) => {
  if (data.type === "progress") {
    $("benchmark-status").textContent = JSON.stringify(data, null, 2);
    return;
  }
  if (data.type === "error" || data.type === "cancelled") {
    pending?.reject(new Error(data.message));
    pending = null;
    return;
  }
  pending?.resolve(data);
  pending = null;
};
worker.onerror = (e) => {
  pending?.reject(new Error(e.message || "The benchmark worker stopped."));
  pending = null;
  $("benchmark-status").textContent =
    e.message || "The benchmark worker stopped.";
};
function controls(busy) {
  $("load-model").disabled = busy;
  $("validate-model").disabled = busy || !report.initialized;
  $("run-benchmark").disabled = busy || !report.validation?.exact;
  $("run-diagnostics").disabled = busy || !report.validation?.exact;
}
async function action(fn) {
  controls(true);
  try {
    await fn();
    $("benchmark-status").textContent = JSON.stringify(summary(), null, 2);
    $("save-benchmark").disabled = false;
  } catch (e) {
    $("benchmark-status").textContent = e.message;
    report.error = e.message;
  } finally {
    controls(false);
  }
}
$("load-model").onclick = () =>
  action(async () => {
    report.initialized = await run({
      type: "initialize",
      url: "./benchmark-data/manifest.json",
    });
  });
$("validate-model").onclick = () =>
  action(async () => {
    report.validation = await run({
      type: "validate",
      url: "./benchmark-data/manifest.json",
    });
  });
$("run-benchmark").onclick = () =>
  action(async () => {
    const r = await fetch("./experiments/encounter-v1/encoding.json");
    if (!r.ok) throw new Error("Recorded inputs unavailable");
    const data = await r.json();
    for (const key of ["a", "b"]) {
      const input = [
        ...Array(75).fill(0),
        ...data.frames[key].map((f) => f.injected_voltage),
        ...Array(150).fill(0),
      ];
      report.results.push(
        await run({
          type: "simulate",
          label: key === "a" ? "Robot" : "Human",
          input,
          seed: 1101,
          capture: true,
        }),
      );
      report.results.at(-1).spoken_seconds =
        data.metadata[key].preprocessing.source_duration_seconds;
      report.results.at(-1).response_sha256 = await responseHashes(
        report.results.at(-1),
      );
    }
    report.within_twice_duration = report.results.every(
      (x) => x.seconds <= 2 * x.spoken_seconds,
    );
  });
$("run-diagnostics").onclick = () =>
  action(async () => {
    const response = await fetch("./browser-model-v1/manifest.json");
    if (!response.ok) throw new Error("Public receiver metadata unavailable");
    const model = await response.json();
    const samples = Float64Array.from({ length: 48000 }, (_, i) =>
      i >= 12000 && i < 36000
        ? 0.1 * Math.sin((2 * Math.PI * 200 * i) / 48000)
        : 0,
    );
    const injection = mechanicalEncoding(samples, model.receiver).injection;
    const records = {};
    for (const name of ["silence", "pulse", "pulse repeat"]) {
      const input = [
        ...Array(75).fill(0),
        ...injection.map((x) => (name === "silence" ? 0 : x)),
        ...Array(150).fill(0),
      ];
      records[name] = await run({
        type: "simulate",
        label: name,
        input,
        seed: 1101,
        capture: true,
      });
    }
    const hashes = {};
    for (const [name, value] of Object.entries(records))
      hashes[name] = await responseHashes(value);
    const p = records.pulse,
      s = records.silence;
    const g = p.group_names.indexOf("direct JON postsynaptic partners");
    const count = (rows) =>
      rows.slice(75, 125).reduce((sum, row) => sum + row[g], 0);
    const downstreamChange =
      (count(p.group_counts) - count(s.group_counts)) / p.group_sizes[g];
    report.diagnostics = {
      stimulus:
        "One second with a 200 Hz, peak 0.1 PCM tone between 0.25 and 0.75 s; original receiver; seed 1101",
      identical_input_exact:
        JSON.stringify(hashes.pulse) === JSON.stringify(hashes["pulse repeat"]),
      silence_is_active: s.counts.some((x) => x > 0),
      downstream_change_spikes_per_second_per_cell: downstreamChange,
      pulse_changes_response: hashes.pulse.spatial !== hashes.silence.spatial,
      nonempty_neural_trajectory: p.spatial.firing_bins.some(
        (x) => x.length > 0,
      ),
      response_sha256: hashes,
    };
  });
$("cancel-benchmark").onclick = () => worker.postMessage({ type: "cancel" });
$("save-benchmark").onclick = () => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(
    new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }),
  );
  a.download = "browser-benchmark.json";
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
};

const $ = (id) => document.getElementById(id),
  worker = new Worker(
    new URL('./browser-benchmark.worker.js', import.meta.url),
    { type: 'module' },
  );
const report = {
  browser: navigator.userAgent,
  hardware_threads: navigator.hardwareConcurrency,
  device_memory_gb: navigator.deviceMemory ?? null,
  results: [],
  visitor_recording_enabled: false,
};
let pending = null;
const run = (data) =>
  new Promise((resolve, reject) => {
    pending = { resolve, reject };
    worker.postMessage(data);
  });
worker.onmessage = ({ data }) => {
  if (data.type === 'progress') {
    $('benchmark-status').textContent = JSON.stringify(data, null, 2);
    return;
  }
  if (data.type === 'error' || data.type === 'cancelled') {
    pending?.reject(new Error(data.message));
    pending = null;
    return;
  }
  pending?.resolve(data);
  pending = null;
};
worker.onerror = (e) => {
  $('benchmark-status').textContent = e.message;
};
function controls(busy) {
  $('load-model').disabled = busy;
  $('validate-model').disabled = busy || !report.initialized;
  $('run-benchmark').disabled = busy || !report.validation?.exact;
}
async function action(fn) {
  controls(true);
  try {
    await fn();
    $('benchmark-status').textContent = JSON.stringify(report, null, 2);
    $('save-benchmark').disabled = false;
    window.benchmarkReport = report;
  } catch (e) {
    $('benchmark-status').textContent = e.message;
    report.error = e.message;
    window.benchmarkReport = report;
  } finally {
    controls(false);
  }
}
$('load-model').onclick = () =>
  action(async () => {
    report.initialized = await run({
      type: 'initialize',
      url: './benchmark-data/manifest.json',
    });
  });
$('validate-model').onclick = () =>
  action(async () => {
    report.validation = await run({
      type: 'validate',
      url: './benchmark-data/manifest.json',
    });
  });
$('run-benchmark').onclick = () =>
  action(async () => {
    const r = await fetch('./experiments/encounter-v1/encoding.json');
    if (!r.ok) throw new Error('Recorded inputs unavailable');
    const data = await r.json();
    for (const key of ['a', 'b']) {
      const input = [
        ...Array(75).fill(0),
        ...data.frames[key].map((f) => f.injected_voltage),
        ...Array(150).fill(0),
      ];
      report.results.push(
        await run({
          type: 'simulate',
          label: key === 'a' ? 'Robot' : 'Human',
          input,
          seed: 1101,
        }),
      );
    }
    report.within_twice_duration = report.results.every(
      (x) => x.seconds <= 2 * x.simulated_seconds,
    );
  });
$('cancel-benchmark').onclick = () => worker.postMessage({ type: 'cancel' });
$('save-benchmark').onclick = () => {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(
    new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }),
  );
  a.download = 'browser-benchmark.json';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
};

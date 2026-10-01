import {
  levelMatch,
  mechanicalInput,
  mono,
  summarize,
  localReading,
} from './local-audio.js';
import { RecordedAudio } from './audio-player.js';
const $ = (id) => document.getElementById(id),
  player = new RecordedAudio();
let worker,
  model,
  context,
  pending,
  stream,
  recorder,
  chunks = [],
  timer,
  cancelled = false,
  busy = false,
  result = null,
  reference = null;
const hash = async (b) =>
  Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', b)), (x) =>
    x.toString(16).padStart(2, '0'),
  ).join('');
const run = (data) =>
  new Promise((resolve, reject) => {
    pending = { resolve, reject };
    worker.postMessage(data);
  });
function initializeWorker() {
  worker = new Worker(
    new URL('./browser-benchmark.worker.js', import.meta.url),
    { type: 'module' },
  );
  worker.onmessage = ({ data }) => {
    if (data.type === 'progress') {
      $('local-status').textContent =
        `${data.stage}${data.fraction !== undefined ? ' · ' + Math.round(data.fraction * 100) + '%' : ''}`;
      return;
    }
    const p = pending;
    pending = null;
    if (data.type === 'error' || data.type === 'cancelled')
      p?.reject(new Error(data.message));
    else p?.resolve(data);
  };
  worker.onerror = (e) => {
    pending?.reject(
      new Error(
        e.message || 'The browser could not allocate or run the model.',
      ),
    );
    pending = null;
    worker.terminate();
    worker = null;
    model = null;
    $('record-controls').hidden = true;
  };
}
function stopTracks() {
  stream?.getTracks().forEach((t) => t.stop());
  stream = null;
  clearTimeout(timer);
}
function controls(state) {
  busy = state;
  $('cancel-local').hidden = !state;
  for (const id of ['record-local', 'example-local', 'local-file'])
    $(id).disabled = state;
  $('load-local').disabled = state || Boolean(model);
}
function fail(e) {
  $('local-error').hidden = false;
  $('local-error').textContent =
    e.name === 'RangeError'
      ? 'Not enough browser memory for this model. Close other tabs or use the recorded encounter.'
      : e.message || String(e);
  $('local-status').textContent = cancelled
    ? 'Cancelled. Your audio has not been uploaded.'
    : 'Unable to complete locally. No recording was uploaded.';
}
async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok)
    throw new Error(
      'The public model or reference is unavailable. Please retry later.',
    );
  return r.json();
}
$('load-local').onclick = async () => {
  controls(true);
  cancelled = false;
  $('local-error').hidden = true;
  try {
    if (
      !isSecureContext ||
      !globalThis.Worker ||
      !globalThis.DecompressionStream ||
      /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent)
    )
      throw new Error(
        'Local simulation is currently qualified for desktop browsers only. The recorded encounter remains available.',
      );
    $('local-status').textContent =
      'Downloading and verifying the full fly model…';
    model = await getJSON('./browser-model-v1/manifest.json');
    if (cancelled) throw new Error('Cancelled');
    if (!worker) initializeWorker();
    await run({
      type: 'initialize',
      url: './browser-model-v1/manifest.json',
      cache: true,
    });
    $('record-controls').hidden = false;
    $('local-status').textContent =
      'The fly is ready. Record yourself or choose a file; all audio stays here.';
  } catch (e) {
    model = null;
    fail(e);
  } finally {
    controls(false);
  }
};
$('cancel-local').onclick = () => {
  cancelled = true;
  worker?.postMessage({ type: 'cancel' });
  if (recorder?.state === 'recording') recorder.stop();
  stopTracks();
  player.pause();
};
async function process(bytes) {
  if (busy || !model) return;
  controls(true);
  cancelled = false;
  $('local-error').hidden = true;
  $('local-result').hidden = true;
  player.pause();
  try {
    if (bytes.byteLength > 64000000)
      throw new Error('Choose a recording below 64 MB.');
    context ||= new AudioContext({ sampleRate: 48000 });
    await context.resume();
    $('local-status').textContent = 'Decoding your recording locally…';
    const decoded = mono(await context.decodeAudioData(bytes.slice(0)));
    if (cancelled) throw new Error('Cancelled');
    if (!reference) {
      const r = await fetch('./experiments/encounter-v1/a.wav');
      if (!r.ok) throw new Error('Synthetic reference audio is unavailable.');
      reference = mono(await context.decodeAudioData(await r.arrayBuffer()));
    }
    const matched = levelMatch(reference, decoded),
      inputs = {
        a: mechanicalInput(matched.a, model.receiver),
        b: mechanicalInput(matched.b, model.receiver),
      },
      records = {};
    for (const name of ['a', 'b']) {
      records[name] = [];
      for (const condition of ['sound', 'silence']) {
        if (cancelled) throw new Error('Cancelled');
        const input = [
          ...Array(75).fill(0),
          ...(condition === 'sound'
            ? inputs[name]
            : Array(inputs[name].length).fill(0)),
          ...Array(150).fill(0),
        ];
        records[name].push(
          await run({
            type: 'simulate',
            input,
            capture: true,
            seed: 1101,
            label: `${name === 'a' ? 'Robot reference' : 'Your voice'} / ${condition}`,
          }),
        );
      }
    }
    const a = summarize(...records.a, 75, Math.ceil(matched.a.length / 960)),
      b = summarize(...records.b, 75, Math.ceil(matched.b.length / 960));
    result = {
      schema_version: 'local-listening-v1',
      model: model.version,
      receiver: model.receiver,
      seed: 1101,
      fly: {
        connectome: 'MaleCNS v1.0',
        upstream_commit: model.upstream_commit,
        configuration: model.configuration,
        rng: 'PCG64',
        array_sha256: Object.fromEntries(
          Object.entries(model.arrays).map(([k, v]) => [k, v.sha256]),
        ),
      },
      recording_sha256: await hash(bytes),
      normalization: { target_rms: matched.target, gains: matched.gains },
      duration: matched.b.length / 48000,
      reference_duration: matched.a.length / 48000,
      encoding: inputs,
      response: { reference: a, visitor: b, raw_runs: records },
      reading: {
        provider: 'numeric-single-run-template-v1',
        input_summary: {
          reference: { mean: a.mean, tail: a.tail },
          visitor: { mean: b.mean, tail: b.tail },
        },
        text: localReading(a, b),
      },
      limitations: [
        'One paired repetition, not a reliable across-seed difference',
        'No semantic or automatic line alignment',
        'Provisional mechanical-to-neural coupling',
        'Browser audio decoding/resampling may differ from Python',
      ],
    };
    player.pause();
    player.context = context;
    player.buffer = context.createBuffer(1, matched.b.length, 48000);
    player.buffer.copyToChannel(Float32Array.from(matched.b), 0);
    player.duration = matched.b.length / 48000;
    player.offset = 0;
    $('local-measurement').textContent =
      `Your voice: ${b.mean.toFixed(3)}; robot: ${a.mean.toFixed(3)} Hz/neuron above matched silence in direct auditory recipients. Different durations remain part of the comparison.`;
    $('local-reading').textContent = result.reading.text;
    $('local-result').hidden = false;
    $('local-status').textContent =
      'Complete. One original-model seeded comparison, computed on this device.';
    draw(0);
  } catch (e) {
    fail(e);
  } finally {
    controls(false);
  }
}
$('local-file').onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  if (file.size > 64000000) {
    fail(new Error('Choose a recording below 64 MB.'));
    return;
  }
  await process(await file.arrayBuffer());
};
$('example-local').onclick = async () => {
  try {
    const r = await fetch('./experiments/encounter-v1/b.wav');
    if (!r.ok) throw new Error('Example unavailable');
    await process(await r.arrayBuffer());
  } catch (e) {
    fail(e);
  }
};
$('record-local').onclick = async () => {
  if (busy) return;
  controls(true);
  cancelled = false;
  $('local-error').hidden = true;
  chunks = [];
  try {
    context ||= new AudioContext({ sampleRate: 48000 });
    await context.resume();
    stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
      },
    });
    if (cancelled) {
      stopTracks();
      controls(false);
      return;
    }
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data);
    };
    recorder.onerror = () => {
      cancelled = true;
      stopTracks();
      controls(false);
      fail(
        new Error(
          'Recording failed. You can choose an existing audio file instead.',
        ),
      );
    };
    recorder.onstop = async () => {
      stopTracks();
      $('stop-local').disabled = true;
      controls(false);
      if (!cancelled)
        await process(
          await new Blob(chunks, { type: recorder.mimeType }).arrayBuffer(),
        );
    };
    recorder.start();
    $('stop-local').disabled = false;
    $('local-status').textContent =
      'Recording on your device · stops automatically at 59 seconds (within the 60-second audio limit).';
    timer = setTimeout(() => recorder.stop(), 59000);
  } catch (e) {
    stopTracks();
    controls(false);
    fail(
      new Error(
        e.name === 'NotAllowedError'
          ? 'Microphone access was declined. Choose an existing recording instead.'
          : e.message,
      ),
    );
  }
};
$('stop-local').onclick = () => {
  if (recorder?.state === 'recording') recorder.stop();
};
$('play-local').onclick = async () => {
  try {
    if (player.paused) await player.play();
    else player.pause();
  } catch (e) {
    fail(e);
  }
};
$('save-local').onclick = () => {
  if (!result) return;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(
    new Blob([JSON.stringify(result)], { type: 'application/json' }),
  );
  a.download = 'my-fly-response.json';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
};
function draw(time) {
  if (!result) return;
  const values = result.response.visitor.rates,
    lo = Math.min(0, ...values),
    hi = Math.max(0.01, ...values),
    scale = hi - lo;
  const pts = [];
  for (let i = 0; i < values.length; i += 5) {
    const slice = values.slice(i, i + 5),
      v = slice.reduce((a, b) => a + b, 0) / slice.length;
    pts.push(`${(i / values.length) * 540},${170 - ((v - lo) / scale) * 155}`);
  }
  const zero = 170 + (lo / scale) * 155,
    x = ((time / 0.02 + 75) / values.length) * 540;
  $('local-trace').innerHTML =
    `<path d="M0 ${zero}H540" stroke="#7c866c" stroke-dasharray="4 4"/><polyline points="${pts.join(' ')}" fill="none" stroke="#8b482b" stroke-width="1.5"/><path d="M${x} 5V175" stroke="#3c5137"/>`;
  $('local-clock').textContent =
    `${time.toFixed(1)} / ${result.duration.toFixed(1)} seconds`;
  $('play-local').textContent = player.paused ? 'PLAY MY RESPONSE' : 'PAUSE';
}
setInterval(() => {
  if (result) draw(player.currentTime);
}, 100);
getJSON('./experiments/encounter-v1/manifest.json')
  .then((m) => {
    $('local-poem').textContent = m.poem;
  })
  .catch(fail);
addEventListener('pagehide', () => {
  stopTracks();
  worker?.terminate();
  player.pause();
});

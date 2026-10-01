import { RecordedAudio } from './audio-player.js';
import { prepareUpload } from './audio-upload.js';
import { parsePassages } from './passage-windows.js';

const $ = (id) => document.getElementById(id);
const audio = new RecordedAudio();
const colors = ['#963f2c', '#326d83'];
let passageStop = null;
let choiceGeneration = 0;
let result,
  encoding,
  base,
  selected = 'a',
  settings,
  loading = false,
  pollTimer;
const fmt = (n) => Number(n).toFixed(3);
const clock = (n) =>
  `${Math.floor(n / 60)}:${Math.floor(n % 60)
    .toString()
    .padStart(2, '0')}`;
function error(message) {
  $('error').textContent = message;
  $('error').hidden = !message;
}
async function json(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') message = body.detail;
    } catch {}
    throw new Error(message);
  }
  return response.json();
}
function link(parent, text, href) {
  const a = document.createElement('a');
  a.textContent = text;
  a.href = href;
  parent.append(a);
}
$('submission').addEventListener('submit', async (event) => {
  event.preventDefault();
  error('');
  $('submit').disabled = true;
  let context;
  try {
    const passages = parsePassages($('windows-a').value, $('windows-b').value);
    context = new AudioContext({ sampleRate: 48000 });
    $('progress-section').hidden = false;
    $('stage').textContent = 'DECODING RECORDINGS';
    const a = await prepareUpload($('file-a').files[0], context),
      b = await prepareUpload($('file-b').files[0], context);
    const metadata = {
      poem: $('poem').value,
      passages,
      label_a: $('label-a').value,
      label_b: $('label-b').value,
      same_poem_attested: $('attestation').checked,
      source_sha256_a: a.hash,
      source_sha256_b: b.hash,
      source_format_a: $('file-a').files[0].type,
      source_format_b: $('file-b').files[0].type,
    };
    const form = new FormData();
    form.append('a', a.blob, 'a.wav');
    form.append('b', b.blob, 'b.wav');
    form.append('metadata', JSON.stringify(metadata));
    const headers = settings.upload_token_required
      ? { Authorization: `Bearer ${$('token').value}` }
      : {};
    const job = await json('api/comparisons', {
      method: 'POST',
      body: form,
      headers,
    });
    history.replaceState(null, '', `?comparison=${encodeURIComponent(job.id)}`);
    $('submission').hidden = true;
    $('example').disabled = true;
    await poll(job.id);
  } catch (e) {
    error(e.message);
    $('progress-section').hidden = true;
  } finally {
    $('submit').disabled = false;
    if (context) await context.close();
  }
});
async function poll(id) {
  try {
    const job = await json(`api/comparisons/${encodeURIComponent(id)}`);
    $('progress-section').hidden = false;
    $('submission').hidden = true;
    $('example').disabled = true;
    $('stage').textContent = job.stage;
    $('progress').value = job.fraction || 0;
    if (job.status === 'complete')
      await load(`api/comparisons/${encodeURIComponent(id)}/`);
    else if (job.status === 'failed') throw new Error(job.error);
    else pollTimer = setTimeout(() => poll(id), 2500);
  } catch (e) {
    error(e.message);
    $('progress-section').hidden = true;
    $('submission').hidden = !settings?.comparisons_enabled;
    $('example').disabled = false;
  }
}
async function load(prefix) {
  choiceGeneration++;
  error('');
  $('example').disabled = $('new').disabled = true;
  loading = true;
  $('play').disabled = true;
  audio.pause();
  try {
    const [next, inputs] = await Promise.all([
      json(`${prefix}result.json`),
      json(`${prefix}encoding.json`),
    ]);
    if (next.schema_version !== 'performance-comparison-v1')
      throw new Error('Unsupported comparison format.');
    result = next;
    encoding = inputs;
    base = prefix;
    $('submission').hidden = true;
    $('progress-section').hidden = true;
    $('results').hidden = false;
    $('comparison-label').textContent =
      `A · ${result.display.label_a} / B · ${result.display.label_b}`;
    $('level-note').textContent =
      `A ${result.audio.a.duration.toFixed(2)} s · B ${result.audio.b.duration.toFixed(2)} s. Shared RMS target ${fmt(result.audio.a.normalization.target_rms)}. Linear gains A ×${fmt(result.audio.a.normalization.gain)}, B ×${fmt(result.audio.b.normalization.gain)}. Mean injected drive A ${fmt(result.audio.a.mean_injected_voltage)}, B ${fmt(result.audio.b.mean_injected_voltage)}.`;
    $('poem-display').textContent = result.display.poem;
    $('population').replaceChildren(
      ...result.response.groups.map((name, i) => {
        const option = new Option(name, i);
        return option;
      }),
    );
    $('population').value = '1';
    renderPassages();
    $('metrics').replaceChildren();
    result.response.differences.forEach((row, i) => {
      const tr = document.createElement('tr');
      [
        row.population,
        fmt(result.response.performances.a.populations[i].rate.mean),
        fmt(result.response.performances.b.populations[i].rate.mean),
        fmt(row.rate.mean),
        `${row.rate.positive} ↑ / ${row.rate.negative} ↓ / ${row.rate.zero} =`,
        fmt(row.tail.mean),
      ].forEach((value) => {
        const td = document.createElement('td');
        td.textContent = value;
        tr.append(td);
      });
      $('metrics').append(tr);
    });
    const primary = result.response.differences[1];
    $('timing-note').textContent =
      `Direct auditory recipients: temporal separation RMS ${fmt(primary.temporal_separation_rms)}; across-seed spread of the paired difference ${fmt(primary.temporal_variability_rms)}. Compared over ${result.response.overlap_seconds.toFixed(1)} shared seconds. Largest average separation begins at ${primary.peak_separation_seconds.toFixed(1)} s (an observed peak, selected after measurement).`;
    $('reading').textContent = result.reading.text;
    $('reading-input').textContent = JSON.stringify(
      result.reading.input_summary,
      null,
      2,
    );
    $('types').replaceChildren(
      ...result.response.exploratory_cell_types.map((row) => {
        const li = document.createElement('li');
        li.textContent = `${row.cell_type}: B − A ${fmt(row.difference.mean)} spikes/s/neuron; ${row.difference.positive} positive / ${row.difference.negative} negative / ${row.difference.zero} zero seeds.`;
        return li;
      }),
    );
    $('limitations').replaceChildren(
      ...result.limitations.map((value) => {
        const li = document.createElement('li');
        li.textContent = value;
        return li;
      }),
    );
    $('downloads').replaceChildren();
    for (const file of [
      'result.json',
      'encoding.json',
      'reading-input.json',
      'a.wav',
      'b.wav',
    ])
      link($('downloads'), file, `${base}${file}`);
    $('raw-links').replaceChildren();
    if (base.startsWith('api/')) {
      for (const name of ['a', 'b'])
        link(
          $('downloads'),
          `Original decoded ${name.toUpperCase()}`,
          `${base}original-${name}.wav`,
        );
      result.runs.forEach((run) => {
        const p = document.createElement('p');
        p.textContent = `${run.id}: `;
        for (const file of ['spikes.npz', 'populations.npz', 'provenance.json'])
          link(p, file, `${base}${run.id}/${file}`);
        $('raw-links').append(p);
      });
    } else
      $('raw-links').textContent =
        'The static replay includes results and input evidence. Large raw spike archives are retained on the simulation host, not copied to GitHub Pages.';
    await choose('a');
    draw();
    $('results').scrollIntoView({ block: 'start' });
  } catch (e) {
    error(e.message);
    throw e;
  } finally {
    loading = false;
    $('play').disabled = false;
    $('example').disabled = $('new').disabled = false;
  }
}
async function choose(name) {
  const generation = ++choiceGeneration;
  passageStop = null;
  $('passage-status').textContent = '';
  selected = name;
  $('choose-a').disabled = $('choose-b').disabled = true;
  document
    .querySelectorAll('#passage-metrics button')
    .forEach((button) => (button.disabled = true));
  $('play').disabled = true;
  try {
    await audio.load(`${base}${name}.wav`);
    if (generation !== choiceGeneration) return false;
    audio.duration = result.audio[name].duration;
    $('seek').max = result.audio[name].duration;
    $('seek').value = 0;
    for (const n of ['a', 'b'])
      $(`choose-${n}`).setAttribute('aria-pressed', String(n === name));
    $('play').textContent = `PLAY ${name.toUpperCase()}`;
    $('play').disabled = false;
    draw();
    return true;
  } finally {
    if (generation === choiceGeneration) {
      $('choose-a').disabled = $('choose-b').disabled = false;
      document
        .querySelectorAll('#passage-metrics button')
        .forEach((button) => (button.disabled = false));
    }
  }
}
for (const name of ['a', 'b'])
  $(`choose-${name}`).addEventListener('click', () =>
    choose(name).catch((e) => error(e.message)),
  );
$('play').addEventListener('click', async () => {
  try {
    if (audio.paused) await audio.play(passageStop);
    else audio.pause();
  } catch (e) {
    error(e.message);
  }
});
$('seek').addEventListener('input', () => {
  passageStop = null;
  $('passage-status').textContent = '';
  audio.currentTime = Number($('seek').value);
  draw();
});
$('population').addEventListener('change', () => {
  renderPassages();
  draw();
});
audio.addEventListener('ended', draw);
audio.addEventListener('pause', draw);
audio.addEventListener('error', () =>
  error('Audio playback failed. Select the recording again to retry.'),
);
$('example').addEventListener('click', () => {
  clearTimeout(pollTimer);
  history.replaceState(null, '', location.pathname);
  load('experiments/performance-v1/').catch(() => {});
});
$('new').addEventListener('click', () => {
  choiceGeneration++;
  audio.pause();
  $('results').hidden = true;
  $('submission').hidden = !settings?.comparisons_enabled;
  history.replaceState(null, '', location.pathname);
  window.scrollTo({ top: 0, behavior: 'smooth' });
});
function renderPassages() {
  const passages = result.response.passage_comparison?.passages || [];
  $('passages').hidden = !passages.length;
  $('passage-metrics').replaceChildren();
  const index = Number($('population').value);
  for (const passage of passages) {
    const row = document.createElement('tr');
    const number = document.createElement('td');
    number.textContent = passage.number;
    row.append(number);
    for (const name of ['a', 'b']) {
      const interval = passage.performances[name];
      const cell = document.createElement('td'),
        button = document.createElement('button');
      button.className = 'secondary';
      button.textContent = `${name.toUpperCase()} ${interval.start.toFixed(2)}–${interval.end.toFixed(2)} s`;
      button.addEventListener('click', async () => {
        try {
          if (!(await choose(name))) return;
          audio.currentTime = interval.start;
          passageStop = interval.end;
          $('passage-status').textContent =
            `Passage ${passage.number} · ${name.toUpperCase()}. Playback stops at ${interval.end.toFixed(2)} seconds.`;
          await audio.play(interval.end);
          draw();
        } catch (e) {
          error(e.message);
        }
      });
      cell.append(button);
      row.append(cell);
    }
    const population = passage.populations[index],
      stats = population.difference;
    const values = [
      `${fmt(passage.performances.a.mean_drive)} / ${fmt(passage.performances.b.mean_drive)}`,
      fmt(stats.mean),
      `${stats.positive} ↑ / ${stats.negative} ↓ / ${stats.zero} =`,
      population.same_direction_across_seeds_and_boundaries
        ? 'Consistent'
        : 'Mixed or zero',
    ];
    for (const value of values) {
      const cell = document.createElement('td');
      cell.textContent = value;
      row.append(cell);
    }
    $('passage-metrics').append(row);
  }
}
function chart(id, series, start, step, unit) {
  const canvas = $(id),
    rect = canvas.getBoundingClientRect(),
    dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, rect.width * dpr);
  canvas.height = rect.height * dpr;
  const c = canvas.getContext('2d');
  c.scale(dpr, dpr);
  const w = rect.width,
    h = rect.height,
    left = 56,
    right = 10,
    top = 22,
    bottom = 28;
  let lo = 0,
    hi = 0.001;
  series.forEach((s) =>
    s.mean.forEach((v, i) => {
      lo = Math.min(lo, v - (s.sd?.[i] || 0));
      hi = Math.max(hi, v + (s.sd?.[i] || 0));
    }),
  );
  const end = Math.max(...series.map((s) => start + s.mean.length * step));
  const x = (t) => left + ((t - start) / (end - start)) * (w - left - right),
    y = (v) => top + ((hi - v) / (hi - lo)) * (h - top - bottom);
  c.font = '11px monospace';
  c.fillStyle = '#60645e';
  c.fillText(`${hi.toFixed(2)} ${unit}`, 0, 12);
  c.fillText(lo.toFixed(2), 0, h - bottom);
  c.strokeStyle = '#c9c9be';
  c.beginPath();
  c.moveTo(left, y(0));
  c.lineTo(w - right, y(0));
  c.stroke();
  for (
    let t = Math.max(0, Math.ceil(start));
    t <= end;
    t += Math.max(1, Math.ceil(end / 6))
  ) {
    c.fillText(`${t}s`, x(t), h - 7);
  }
  series.forEach((s, k) => {
    if (s.sd) {
      c.fillStyle = `${colors[k]}22`;
      c.beginPath();
      s.mean.forEach((v, i) => {
        const px = x(start + i * step);
        if (!i) c.moveTo(px, y(v + s.sd[i]));
        else c.lineTo(px, y(v + s.sd[i]));
      });
      for (let i = s.mean.length - 1; i >= 0; i--)
        c.lineTo(x(start + i * step), y(s.mean[i] - s.sd[i]));
      c.closePath();
      c.fill();
    }
    c.strokeStyle = colors[k];
    c.lineWidth = 1.2;
    c.beginPath();
    s.mean.forEach((v, i) => {
      if (!i) c.moveTo(x(start), y(v));
      else c.lineTo(x(start + i * step), y(v));
    });
    c.stroke();
    c.setLineDash([3, 4]);
    const finish = result.audio[k ? 'b' : 'a'].duration;
    c.beginPath();
    c.moveTo(x(finish), top);
    c.lineTo(x(finish), h - bottom);
    c.stroke();
    c.setLineDash([]);
  });
  const cursor = audio.currentTime || 0;
  c.strokeStyle = '#262b29';
  c.lineWidth = 1;
  c.beginPath();
  c.moveTo(x(cursor), top);
  c.lineTo(x(cursor), h - bottom);
  c.stroke();
}
function draw() {
  if (!result || $('results').hidden) return;
  const j = Number($('population').value);
  chart(
    'trace',
    ['a', 'b'].map((name) => {
      const row = result.response.performances[name].timeline;
      return { mean: row.mean.map((v) => v[j]), sd: row.sd.map((v) => v[j]) };
    }),
    -1,
    0.1,
    'Hz/neuron',
  );
  for (const [id, field, unit] of [
    ['envelope', 'rms', 'RMS'],
    ['injection', 'injected_voltage', 'drive'],
  ])
    chart(
      id,
      ['a', 'b'].map((name) => ({
        mean: encoding.frames[name].map((row) => row[field]),
      })),
      0,
      0.02,
      unit,
    );
  $('clock').textContent =
    `${clock(audio.currentTime || 0)} / ${clock(result.audio[selected].duration)}`;
}
let lastPaint = 0;
function tick(now) {
  if (result && !loading && now - lastPaint > 100) {
    if (passageStop !== null && audio.currentTime >= passageStop) {
      const end = passageStop;
      passageStop = null;
      audio.pause();
      audio.currentTime = end;
      draw();
    }
    $('seek').value = audio.currentTime || 0;
    $('play').textContent =
      `${audio.paused ? 'PLAY' : 'PAUSE'} ${selected.toUpperCase()}`;
    if (!audio.paused) draw();
    lastPaint = now;
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
window.addEventListener('resize', draw);
async function init() {
  const id = new URLSearchParams(location.search).get('comparison');
  $('example').disabled = true;
  try {
    settings = await json('api/settings');
    $('availability').textContent = settings.comparisons_enabled
      ? 'Simulation service connected. Four paired runs per performance; allow several minutes.'
      : 'This host has not enabled recording uploads. The recorded comparison remains playable.';
    $('submission').hidden = !settings.comparisons_enabled || Boolean(id);
    $('token-label').hidden = !settings.upload_token_required;
    $('retention').textContent = settings.public
      ? 'Recordings and results are available to anyone with the result link. Links expire after 24 hours; expired data is deleted on subsequent submissions. Keep a local copy.'
      : 'Local mode: recordings and results persist in this computer’s results folder. Anyone able to reach this server and holding a result link can access them.';
    const example = await json('api/example');
    $('poem').value = example.poem;
  } catch {
    settings = { comparisons_enabled: false };
    $('availability').textContent =
      'This is the recorded online edition. GitHub Pages can replay evidence but cannot receive audio or run the Python simulation. Use the local application to compare your recordings.';
  }
  if (id) await poll(id);
  else $('example').disabled = false;
}
init();

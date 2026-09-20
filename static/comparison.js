import { RecordedAudio } from './audio-player.js';
import { describeContrast } from './delivery-reading.js';
const $ = (id) => document.getElementById(id);
const base = new URL('.', import.meta.url);
const root = new URL('experiments/delivery-v1/', base);
const url = (path) => new URL(path, root).href;
const load = async (path) => {
  const r = await fetch(url(path), { cache: 'no-cache' });
  if (!r.ok) throw new Error(`Evidence unavailable (${r.status})`);
  return r.json();
};
const node = (tag, text) => {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  return n;
};
const fmt = (n) => (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(4);
const refColor = '#39635d',
  otherColor = '#a55235';
let data,
  selected = 'human',
  population = 2,
  frames = {},
  waves = {},
  charts = [];
const audioL = new RecordedAudio(),
  audioR = new RecordedAudio();
let activeAudio = audioL;
function svg(tag, props, text) {
  const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(props)) n.setAttribute(k, v);
  if (text !== undefined) n.textContent = text;
  return n;
}
function plot(id, series, { zero = true, endings = [] } = {}) {
  const el = $(id),
    height = Number(el.getAttribute('viewBox').split(' ')[3]),
    bottom = height - 30;
  el.replaceChildren();
  const maxT = Math.max(...series.map((s) => s.time.at(-1)), ...endings, 1);
  const vals = series.flatMap((s) => [...s.low, ...s.high]);
  let lo = Math.min(...vals, 0),
    hi = Math.max(...vals, 0);
  if (hi - lo < 0.00001) {
    lo = -0.001;
    hi = 0.001;
  }
  const pad = (hi - lo) * 0.08;
  lo -= pad;
  hi += pad;
  const x = (t) => 65 + (t / maxT) * 910,
    y = (v) => bottom - ((v - lo) / (hi - lo)) * (bottom - 20);
  for (const value of [lo, (lo + hi) / 2, hi])
    el.append(
      svg(
        'text',
        { x: 0, y: y(value) + 4, fill: '#62675d', 'font-size': 12 },
        value.toFixed(3),
      ),
    );
  if (zero)
    el.append(
      svg('line', {
        x1: 65,
        x2: 975,
        y1: y(0),
        y2: y(0),
        stroke: '#b9bcb3',
        'stroke-dasharray': '4 4',
      }),
    );
  for (const s of series) {
    const points = s.time
      .map((t, i) => `${x(t)},${y(s.high[i])}`)
      .concat(s.time.map((t, i) => `${x(t)},${y(s.low[i])}`).reverse())
      .join(' ');
    el.append(svg('polygon', { points, fill: s.color, opacity: 0.14 }));
    if (s.mean)
      el.append(
        svg('polyline', {
          points: s.time.map((t, i) => `${x(t)},${y(s.mean[i])}`).join(' '),
          fill: 'none',
          stroke: s.color,
          'stroke-width': 1.5,
        }),
      );
  }
  endings.forEach((t, i) =>
    el.append(
      svg('line', {
        x1: x(t),
        x2: x(t),
        y1: 12,
        y2: bottom,
        stroke: i ? otherColor : refColor,
        'stroke-dasharray': '3 5',
      }),
    ),
  );
  for (let i = 0; i <= 4; i++)
    el.append(
      svg(
        'text',
        {
          x: x((i * maxT) / 4),
          y: height - 5,
          'text-anchor': i === 4 ? 'end' : 'start',
          fill: '#62675d',
          'font-size': 12,
        },
        `${((i * maxT) / 4).toFixed(1)} s`,
      ),
    );
  const cursor = svg('line', {
    x1: 65,
    x2: 65,
    y1: 12,
    y2: bottom,
    stroke: '#262923',
    'stroke-width': 1,
    visibility: 'hidden',
  });
  el.append(cursor);
  charts.push({ cursor, x, maxT });
}
function trace(name, j) {
  const t = data.traces[name];
  return {
    time: t.time,
    mean: t.mean.map((r) => r[j]),
    low: t.low.map((r) => r[j]),
    high: t.high.map((r) => r[j]),
    color: name === 'reference' ? refColor : otherColor,
  };
}
function render() {
  charts = [];
  const conditions = data.manifest.conditions,
    c = conditions[selected],
    j = population,
    pop = data.populations[j],
    contrast = data.contrasts[selected].populations[pop],
    m = contrast.mean;
  $('right-label').textContent = c.label;
  $('metric-title').textContent =
    `${pop} · comparison minus reference, after each matched-silence subtraction`;
  $('metrics').replaceChildren(
    ...[
      [
        'Mean rate difference',
        fmt(m.mean),
        `paired SD ${m.sd.toFixed(4)} Hz/neuron`,
      ],
      [
        'Direction across seeds',
        `${m.positive} + / ${m.negative} − / ${m.zero} zero`,
        `${data.seeds.length} paired seeds`,
      ],
      [
        'One-second aftermath',
        fmt(contrast.tail.mean),
        `paired SD ${contrast.tail.sd.toFixed(4)} Hz/neuron`,
      ],
    ].map(([label, value, caption]) => {
      const n = node('div');
      n.className = 'metric';
      const v = node('span', value);
      v.className = 'value';
      const small = node('span', caption);
      small.className = 'caption';
      n.append(node('span', label), v, small);
      return n;
    }),
  );
  const agreement = Math.max(m.positive, m.negative),
    consistent = agreement === data.seeds.length && Math.abs(m.mean) > m.sd;
  $('verdict').textContent =
    m.zero === data.seeds.length
      ? 'No paired difference in this metric at any seed.'
      : consistent
        ? `The rate difference has the same direction in all ${data.seeds.length} seeds, and its absolute mean exceeds its across-seed SD.`
        : `This metric does not pass the bench’s descriptive consistency check: all seeds in one direction and absolute mean greater than paired SD.`;
  $('reading').textContent = describeContrast(m, data.seeds.length);
  for (const [side, name] of [
    ['left', 'reference'],
    ['right', selected],
  ]) {
    const a = conditions[name];
    $('exposure-' + side).textContent =
      `${a.duration.toFixed(2)} s · RMS ${a.normalization.output_rms.toFixed(6)} · gain ${a.normalization.gain.toFixed(4)} · mean drive ${a.mean_injection.toFixed(4)} · integrated drive ${a.integrated_injection.toFixed(3)} model-units·s · ${a.capped_frames} capped frames`;
  }
  plot('response-chart', [trace('reference', j), trace(selected, j)], {
    endings: [conditions.reference.duration, c.duration],
  });
  const d = data.contrasts[selected].paired_trace;
  const temporal = data.contrasts[selected].temporal_pattern[pop];
  $('temporal-summary').textContent =
    `RMS of the mean paired trace: ${temporal.mean_trace_rms.toFixed(4)} Hz/neuron. RMS of pointwise seed SD: ${temporal.seed_sd_rms.toFixed(4)} Hz/neuron. This compares temporal separation with variability; it does not require a change in the overall mean rate.`;
  plot('difference-chart', [
    {
      time: d.time,
      mean: d.mean.map((r) => r[j]),
      low: d.low.map((r) => r[j]),
      high: d.high.map((r) => r[j]),
      color: otherColor,
    },
  ]);
  plot(
    'wave-chart',
    ['reference', selected].map((name) => ({
      time: waves[name].map((_, i) => i * 0.02),
      low: waves[name].map((r) => r[0]),
      high: waves[name].map((r) => r[1]),
      color: name === 'reference' ? refColor : otherColor,
    })),
  );
  plot(
    'input-chart',
    ['reference', selected].map((name) => ({
      time: frames[name].map((r) => r.time),
      mean: frames[name].map((r) => r.injected_voltage),
      low: frames[name].map((r) => r.injected_voltage),
      high: frames[name].map((r) => r.injected_voltage),
      color: name === 'reference' ? refColor : otherColor,
    })),
  );
  $('recruitment').replaceChildren(
    ...data.contrasts[selected].recruitment.map((r) => {
      const row = node('tr');
      [
        r.name,
        r.neurons,
        fmt(r.mean),
        r.sd.toFixed(4),
        `${r.positive} / ${r.negative} / ${r.zero}`,
      ].forEach((v) => row.append(node('td', v)));
      return row;
    }),
  );
  $('seed-table').replaceChildren(
    ...data.seeds.map((seed, i) => {
      const row = node('tr');
      [
        seed,
        fmt(data.metrics.reference[i].mean[j]),
        fmt(data.metrics[selected][i].mean[j]),
        fmt(m.values[i]),
      ].forEach((v) => row.append(node('td', v)));
      return row;
    }),
  );
  const text = data.manifest.poem.split('\n');
  $('lines').replaceChildren(
    ...conditions.reference.lines
      .filter((line) => text[line.line - 1]?.trim())
      .map((line) => {
        const b = node('button', `${line.line}. ${text[line.line - 1]}`);
        b.type = 'button';
        b.addEventListener('click', () => {
          audioL.pause();
          audioR.pause();
          audioL.currentTime = line.start;
          const other = c.lines.find((l) => l.line === line.line);
          if (other) audioR.currentTime = other.start;
          updateCursor(line.start);
        });
        return b;
      }),
  );
  $('downloads').replaceChildren(
    ...[
      ['PROTOCOL.md', 'Protocol'],
      ['manifest.json', 'Stimuli and normalization'],
      ['pilot.json', 'Pilot and replication choice'],
      ['comparison.json', 'All response summaries'],
      ['counts.npz', 'Recorded counts for all seeds'],
      ['raw-artifacts.json', 'Local spike archive manifest'],
      ['sources/reference.wav', 'Original synthetic PCM'],
      ['sources/human.wav', 'Original human PCM'],
      [`${selected}/encoding.json`, 'Every comparison injection'],
      [`${selected}/audio.wav`, 'Processed comparison WAV'],
    ].map(([path, label]) => {
      const a = node('a', label + ' ↗');
      a.href = url(path);
      return a;
    }),
  );
}
function updateCursor(t) {
  for (const c of charts) {
    c.cursor.setAttribute('visibility', t <= c.maxT ? 'visible' : 'hidden');
    c.cursor.setAttribute('x1', c.x(t));
    c.cursor.setAttribute('x2', c.x(t));
  }
}
for (const [side, a, b] of [
  ['left', audioL, audioR],
  ['right', audioR, audioL],
]) {
  $('play-' + side).addEventListener('click', async () => {
    if (!a.paused) {
      a.pause();
      return;
    }
    const button = $('play-' + side);
    button.disabled = true;
    try {
      b.pause();
      activeAudio = a;
      await a.play();
    } catch (e) {
      $('status').hidden = false;
      $('status').textContent = `Playback failed: ${e.message}`;
    } finally {
      button.disabled = false;
    }
  });
  $('seek-' + side).addEventListener('input', () => {
    a.currentTime = Number($('seek-' + side).value);
    activeAudio = a;
    updateCursor(a.currentTime);
  });
  a.addEventListener('play', () => {
    $('play-' + side).textContent = 'PAUSE';
  });
  a.addEventListener('pause', () => {
    $('play-' + side).textContent =
      side === 'left' ? 'PLAY REFERENCE' : 'PLAY COMPARISON';
  });
  a.addEventListener('ended', () => {
    $('play-' + side).textContent = 'REPLAY';
  });
}
function animate() {
  for (const [side, a] of [
    ['left', audioL],
    ['right', audioR],
  ]) {
    $('seek-' + side).value = a.currentTime;
    $('time-' + side).textContent =
      `${a.currentTime.toFixed(2)} / ${a.duration.toFixed(2)} s`;
  }
  updateCursor(activeAudio.currentTime);
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);

async function choose() {
  for (const section of $('bench').querySelectorAll('section,details'))
    section.hidden = true;
  audioL.pause();
  audioR.pause();
  for (const side of ['left', 'right']) {
    $('play-' + side).disabled = true;
    $('seek-' + side).disabled = true;
  }
  $('condition').disabled = true;
  $('population').disabled = true;
  $('status').hidden = false;
  $('status').textContent = 'Loading the selected acoustic evidence…';
  try {
    selected = $('condition').value;
    for (const name of ['reference', selected]) {
      if (!frames[name]) {
        [frames[name], waves[name]] = await Promise.all([
          load(`${name}/encoding.json`),
          load(`${name}/waveform.json`),
        ]);
      }
    }
    await Promise.all([
      audioL.load(url('reference/audio.wav')),
      audioR.load(url(`${selected}/audio.wav`)),
    ]);
    audioL.duration = data.manifest.conditions.reference.duration;
    audioR.duration = data.manifest.conditions[selected].duration;
    for (const [side, a] of [
      ['left', audioL],
      ['right', audioR],
    ]) {
      $('seek-' + side).max = a.duration;
      $('play-' + side).disabled = false;
      $('seek-' + side).disabled = false;
    }
    render();
    for (const section of $('bench').querySelectorAll('section,details'))
      section.hidden = false;
    $('status').hidden = true;
  } catch (e) {
    $('status').textContent = e.message;
  } finally {
    $('condition').disabled = false;
    $('population').disabled = false;
  }
}
$('condition').addEventListener('change', choose);
$('population').addEventListener('change', () => {
  population = Number($('population').value);
  render();
});
try {
  data = await load('comparison.json');
  for (const [name, c] of Object.entries(data.manifest.conditions)) {
    if (name === 'reference') continue;
    const o = node('option', c.label);
    o.value = name;
    $('condition').append(o);
  }
  data.populations.forEach((name, i) => {
    const o = node('option', name);
    o.value = i;
    $('population').append(o);
  });
  $('population').value = population;
  $('design').textContent =
    `${data.seeds.length} seeds (${data.seeds.join(', ')}). Seven conditions, each with matched silence. Reference and diagnostic contrasts have equal duration; the human performance remains longer.`;
  $('exact').textContent =
    `${data.exact_controls.filter((c) => c.spikes_identical).length} / ${data.exact_controls.length} independently simulated repeat/polarity controls match the reference raw spike arrays exactly.`;
  $('bench').hidden = false;
  await choose();
} catch (e) {
  $('status').textContent = `Comparison unavailable: ${e.message}`;
}

const $ = (id) => document.getElementById(id);
const base = './experiments/temporal-v2/';
const notes = {
  human:
    'Denny Sayers’ rendition versus the synthetic reference. Equal waveform RMS; different duration, pacing and total injected drive. This comparison cannot isolate any single delivery feature.',
  pauses:
    'Redistributed pauses in the synthetic recording. Spoken samples and total duration are preserved; timing changes.',
  reordered:
    'Reordered source-line segments. This diagnostic preserves their contents and total duration; it is not a natural alternative rendition.',
  localized:
    'One relocated pause. This is a local intervention in delivery, preserving every speech sample and total duration.',
  frame_reverse:
    'Encoder-only control: the same injected values in reverse order. Exact total drive and value distribution are preserved. There is no corresponding oral recording; this tests temporal arrangement at the receiver’s input boundary.',
};
const n = (value) => Number(value).toFixed(3);
function rows(id, values) {
  $(id).replaceChildren(
    ...values.map((row) => {
      const tr = document.createElement('tr');
      for (const value of row) {
        const td = document.createElement('td');
        td.textContent = value;
        tr.append(td);
      }
      return tr;
    }),
  );
}
function plot(trace) {
  const svg = $('trace');
  svg.replaceChildren();
  const ns = 'http://www.w3.org/2000/svg';
  const extent = Math.max(
    0.001,
    ...trace.low.map(Math.abs),
    ...trace.high.map(Math.abs),
  );
  const x = (i) => 65 + (i / Math.max(1, trace.time.length - 1)) * 900;
  const y = (value) => 120 - (value / extent) * 95;
  const add = (tag, attrs, text) => {
    const e = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs))
      e.setAttribute(key, value);
    if (text !== undefined) e.textContent = text;
    svg.append(e);
  };
  const points = (a) => a.map((v, i) => `${x(i)},${y(v)}`);
  add('polygon', {
    points: [...points(trace.high), ...points(trace.low).reverse()].join(' '),
    fill: '#a5523526',
  });
  add('line', {
    x1: 65,
    x2: 965,
    y1: 120,
    y2: 120,
    stroke: '#777',
    'stroke-dasharray': '4 4',
  });
  add('polyline', {
    points: points(trace.mean).join(' '),
    fill: 'none',
    stroke: '#a55235',
    'stroke-width': 1.8,
  });
  for (const value of [-extent, 0, extent])
    add('text', { x: 0, y: y(value) + 4, 'font-size': 12 }, n(value));
  for (const i of [0, Math.floor(trace.time.length / 2), trace.time.length - 1])
    add(
      'text',
      { x: x(i), y: 245, 'text-anchor': 'middle', 'font-size': 12 },
      `${trace.time[i].toFixed(1)} s`,
    );
}
function render(data) {
  const key = $('condition').value;
  const result = data.comparisons[key];
  const direct = result.populations['direct JON postsynaptic partners'];
  const condition = data.manifest.conditions[key];
  const reference = data.manifest.conditions.reference;
  $('condition-note').textContent = notes[key];
  $('exposure').textContent =
    `Duration: ${condition.duration.toFixed(2)} s / reference ${reference.duration.toFixed(2)} s. Integrated injected drive: ${n(condition.integrated_drive)} / reference ${n(reference.integrated_drive)} model drive·s.`;
  $('measurement').textContent = result.reading.measurement;
  $('functional').textContent = result.reading.functional_limit;
  $('reading').textContent = result.reading.affect_reading;
  $('qualification').textContent = result.reading.qualification;
  rows(
    'criteria',
    ['direct JON postsynaptic partners', 'descending_neuron'].map((g) => {
      const t = result.populations[g].temporal;
      return [
        g,
        n(t.mean_trace_rms),
        n(t.seed_sd_rms),
        n(t.split_half_cosine),
        t.criterion_met ? 'Met' : 'Not met',
      ];
    }),
  );
  rows(
    'episodes',
    result.episodes.map((e) => [
      `${e.start.toFixed(1)}–${e.end.toFixed(1)} s`,
      `${n(e.mean)} Hz/neuron`,
      `${e.positive} higher · ${e.negative} lower · ${8 - e.positive - e.negative} equal`,
    ]),
  );
  plot(result.trace);
  $('local-section').hidden = key !== 'localized';
  const onset =
    data.localized_resumption.populations['direct JON postsynaptic partners'];
  $('resumption').textContent =
    `The onset-associated downstream contrast changed by ${n(onset.mean)} Hz/neuron on average (SD ${n(onset.sd)}): ${onset.positive} repetitions higher, ${onset.negative} lower, ${onset.zero} unchanged.`;
  $('tail').textContent =
    `Across all five seconds, the average downstream difference is ${n(direct.tail.mean)} Hz/neuron (SD ${n(direct.tail.sd)}). Inspect its course below rather than treating this average as an aftereffect by itself.`;
  rows(
    'tail-bins',
    direct.tail_seconds.map((r, i) => [
      `${i}–${i + 1} s`,
      n(r.mean),
      `${r.positive} / ${r.negative} / ${r.zero}`,
    ]),
  );
  rows(
    'circuits',
    ['DNa02', 'DNp01', 'MDN', 'pIP10'].map((g) => {
      const t = result.populations[g].temporal;
      return [
        g,
        `${n(t.mean_trace_rms)} / ${n(t.seed_sd_rms)}`,
        n(t.split_half_cosine),
        t.criterion_met ? 'Met' : 'Not met',
      ];
    }),
  );
  $('interpretation-input').href = `${base}${key}-interpretation-input.json`;
}
try {
  const response = await fetch(`${base}confirmation.json`);
  if (!response.ok)
    throw new Error(`Response data unavailable (${response.status})`);
  const data = await response.json();
  for (const key of Object.keys(data.comparisons)) {
    const option = document.createElement('option');
    option.value = key;
    option.textContent = data.manifest.conditions[key].label;
    $('condition').append(option);
  }
  $('condition').addEventListener('change', () => render(data));
  render(data);
  $('report').hidden = false;
  $('status').hidden = true;
} catch (error) {
  $('status').textContent = `Unable to load this experiment: ${error.message}`;
}

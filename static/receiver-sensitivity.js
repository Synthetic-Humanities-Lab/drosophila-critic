// Separate experimental report: never changes the production poem receiver.
const root = document.querySelector('#sensitivity');
const ns = 'http://www.w3.org/2000/svg';
function element(tag, text, parent) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  parent.append(node);
  return node;
}
function svgElement(tag, attrs, parent, text) {
  const node = document.createElementNS(ns, tag);
  for (const [key, value] of Object.entries(attrs))
    node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  parent.append(node);
  return node;
}
function trace(container, report, arm, group) {
  container.replaceChildren();
  const records = ['reference', 'human'].map(
    (n) => report.conditions[`${n}-${arm}`],
  );
  const extent = Math.max(
    ...records.flatMap((r) =>
      [...r.trace_100ms.min, ...r.trace_100ms.max].map((row) =>
        Math.abs(row[group]),
      ),
    ),
    0.001,
  );
  const end = Math.max(...records.map((r) => r.time_seconds.at(-1) + 0.1));
  records.forEach((r, index) => {
    element(
      'h3',
      index ? 'Human performance' : 'Synthetic reference',
      container,
    );
    const svg = svgElement(
      'svg',
      {
        viewBox: '0 0 900 220',
        role: 'img',
        'aria-label': `${index ? 'Human' : 'Synthetic'} silence-corrected firing rate; shaded min/max across seeds`,
      },
      container,
    );
    const xy = (v, i) =>
      `${65 + (r.time_seconds[i] / end) * 815},${105 - (v[group] / extent) * 80}`;
    const upper = r.trace_100ms.max.map(xy);
    const lower = r.trace_100ms.min.map(xy).reverse();
    svgElement(
      'path',
      {
        d: `M${upper.concat(lower).join('L')}Z`,
        fill: '#91472f',
        opacity: 0.18,
      },
      svg,
    );
    svgElement(
      'path',
      {
        d: `M${r.trace_100ms.mean.map(xy).join('L')}`,
        fill: 'none',
        stroke: '#91472f',
        'stroke-width': 1.5,
      },
      svg,
    );
    svgElement(
      'line',
      {
        x1: 65,
        x2: 880,
        y1: 105,
        y2: 105,
        stroke: '#666',
        'stroke-dasharray': '3 3',
      },
      svg,
    );
    const stop = 65 + (r.metadata.duration / end) * 815;
    svgElement(
      'line',
      { x1: stop, x2: stop, y1: 20, y2: 185, stroke: '#333' },
      svg,
    );
    [
      [2, 25, `+${extent.toFixed(2)}`],
      [2, 110, '0'],
      [2, 185, `−${extent.toFixed(2)}`],
      [65, 211, '0 s'],
      [780, 211, `${end.toFixed(1)} s`],
    ].forEach(([x, y, label]) =>
      svgElement('text', { x, y, 'font-size': 13 }, svg, label),
    );
  });
  element(
    'p',
    'Hz per neuron above matched silence. Same axes; native elapsed time, not aligned poem lines. Shading is the range of four seeds, not a confidence interval. Vertical lines mark the voice stopping.',
    container,
  );
}
async function load() {
  const response = await fetch(
    './experiments/receiver-v2/sensitivity/comparison.json',
    { cache: 'no-store' },
  );
  if (!response.ok)
    throw new Error(`Sensitivity report unavailable (${response.status})`);
  const report = await response.json();
  root.replaceChildren();
  element('h2', 'What changes when we change the receiver?', root);
  element(
    'p',
    'A provisional adapter now connects modeled antennal motion to the original frozen connectome. Its input strength is an engineering choice, not a physiological calibration. The production poem readings still use the original amplitude receiver.',
    root,
  );
  element(
    'p',
    `Exact repeated-input spike check: ${report.repeat_exact_spikes ? 'passed' : 'FAILED'}. ${report.seeds.length} seeds; original 20 ms neural clock. No literary interpretation is generated from this pilot.`,
    root,
  );
  const contrasts = Object.values(report.human_minus_reference);
  const lowerDrive = Object.keys(report.human_minus_reference).every((arm) => {
    const mean = (name) => {
      const m = report.conditions[`${name}-${arm}`].metadata;
      return m.integrated_drive / (m.sound_frames + m.decay_frames);
    };
    return mean('human') < mean('reference');
  });
  if (lowerDrive && contrasts.every((row) => row.max[1] < 0)) {
    element(
      'p',
      'Across this pilot, the human rendition produces a lower average silence-corrected rate in direct auditory partners at every tested receiver setting and seed. Its average injected drive is also lower: this does not establish a response beyond mean stimulation.',
      root,
    );
  }
  if (
    !contrasts.every((row) => row.min[2] > 0) &&
    !contrasts.every((row) => row.max[2] < 0)
  ) {
    element(
      'p',
      'Descending-neuron activity has no common direction across all settings and seeds. These results do not support a stable movement disposition for either rendition.',
      root,
    );
  }
  const label = element('label', 'Neural population ', root);
  const group = element('select', undefined, label);
  report.groups.forEach((name, i) => {
    const o = element('option', name, group);
    o.value = i;
  });
  group.value = '1';
  const armLabel = element('label', ' Receiver ', root);
  const arm = element('select', undefined, armLabel);
  Object.keys(report.human_minus_reference).forEach((name) =>
    element('option', name, arm),
  );
  const chart = element('div', undefined, root);
  const tableContainer = element('div', undefined, root);
  tableContainer.className = 'scroll';
  const draw = () => {
    trace(chart, report, arm.value, Number(group.value));
    tableContainer.replaceChildren();
    element(
      'h3',
      'Human minus synthetic: mean rate during sound',
      tableContainer,
    );
    element(
      'p',
      'Both recordings minus their own equal-duration silence. Positive means a higher mean rate for the human performance. Different durations and acoustic structures remain confounded.',
      tableContainer,
    );
    const table = element('table', undefined, tableContainer);
    const header = element('tr', undefined, element('thead', undefined, table));
    [
      'Receiver / strength',
      'Mean Δ Hz/neuron',
      'Seed range',
      'Positive / negative seeds',
      'Capped frames: synthetic / human',
    ].forEach((s) => element('th', s, header));
    const body = element('tbody', undefined, table);
    const g = Number(group.value);
    Object.entries(report.human_minus_reference).forEach(([name, s]) => {
      const row = element('tr', undefined, body);
      const positive = s.per_seed.filter((r) => r[g] > 0).length;
      const negative = s.per_seed.filter((r) => r[g] < 0).length;
      [
        name,
        s.mean[g].toFixed(4),
        `${s.min[g].toFixed(4)} … ${s.max[g].toFixed(4)}`,
        `${positive} / ${negative}`,
        `${report.conditions[`reference-${name}`].metadata.capped_frames} / ${report.conditions[`human-${name}`].metadata.capped_frames}`,
      ].forEach((v) => element('td', v, row));
    });
    element(
      'h3',
      'Controlled frequency contrast: 800 minus 200 Hz',
      tableContainer,
    );
    Object.entries(report.tone800_minus_200).forEach(([name, s]) =>
      element(
        'p',
        `${name}: ${s.mean[g].toFixed(4)} Hz/neuron; seed range ${s.min[g].toFixed(4)} … ${s.max[g].toFixed(4)}.`,
        tableContainer,
      ),
    );
  };
  group.addEventListener('change', draw);
  arm.addEventListener('change', draw);
  draw();
  const links = element('p', undefined, root);
  [
    ['Protocol', 'PROTOCOL.md'],
    ['Result JSON', 'comparison.json'],
    ['Full injected inputs', 'inputs.json'],
    ['Findings', 'FINDINGS.md'],
  ].forEach(([label, file]) => {
    const a = element('a', label, links);
    a.href = `./experiments/receiver-v2/sensitivity/${file}`;
    links.append(' · ');
  });
}
load().catch((error) => {
  root.textContent = error.message;
  root.setAttribute('role', 'alert');
});

const root = document.querySelector('#order-report');
function add(tag, text, parent) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  parent.append(e);
  return e;
}
function svg(tag, attrs, parent, text) {
  const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text !== undefined) e.textContent = text;
  parent.append(e);
  return e;
}
function plot(parent, series, group, duration, label) {
  add('h3', label, parent);
  const chart = svg(
    'svg',
    { viewBox: '0 0 900 240', role: 'img', 'aria-label': label },
    parent,
  );
  const scale = Math.max(
    0.001,
    ...series.min.map((x) => Math.abs(x[group])),
    ...series.max.map((x) => Math.abs(x[group])),
  );
  const xy = (row, i) =>
    `${65 + ((i * 0.1) / duration) * 815},${110 - (row[group] / scale) * 85}`;
  svg(
    'path',
    {
      d:
        'M' +
        series.max.map(xy).concat(series.min.map(xy).reverse()).join('L') +
        'Z',
      fill: '#91472f',
      opacity: 0.18,
    },
    chart,
  );
  svg(
    'path',
    {
      d: 'M' + series.mean.map(xy).join('L'),
      fill: 'none',
      stroke: '#91472f',
      'stroke-width': 1.5,
    },
    chart,
  );
  svg(
    'line',
    {
      x1: 65,
      x2: 880,
      y1: 110,
      y2: 110,
      stroke: '#555',
      'stroke-dasharray': '3 3',
    },
    chart,
  );
  [
    [2, 25, `+${scale.toFixed(3)}`],
    [2, 115, '0'],
    [2, 200, `−${scale.toFixed(3)}`],
    [65, 230, '0 s'],
    [790, 230, `${duration.toFixed(2)} s`],
  ].forEach(([x, y, t]) => svg('text', { x, y, 'font-size': 13 }, chart, t));
}
async function load() {
  const response = await fetch(
    './experiments/receiver-v2/order/comparison.json',
    { cache: 'no-store' },
  );
  if (!response.ok) throw new Error(`Report unavailable (${response.status})`);
  const r = await response.json();
  root.replaceChildren();
  add(
    'p',
    `${Object.keys(r.runs).length} full-connectome runs. Exact repeated-input spike check: ${r.repeat_exact_spikes ? 'passed' : 'FAILED'}. Stimulus duration: ${r.input_duration_seconds.toFixed(2)} s; neural tail: ${r.tail_seconds} s.`,
    root,
  );
  const label = add('label', 'Population ', root),
    group = add('select', undefined, label);
  r.groups.forEach((name, i) => {
    const o = add('option', name, group);
    o.value = i;
  });
  group.value = 1;
  const choice = add('label', 'Contrast ', root),
    condition = add('select', undefined, choice);
  Object.keys(r.comparisons).forEach((name) => add('option', name, condition));
  const content = add('div', undefined, root);
  function draw() {
    content.replaceChildren();
    const g = Number(group.value);
    const c = r.comparisons[condition.value];
    add('h2', 'Whole-stimulus and tail differences', content);
    add(
      'p',
      'Each condition minus original, in Hz per neuron. Both are corrected against the same-seed silence. The original, reverse and shuffle inputs have identical value distributions; constant input has a different distribution.',
      content,
    );
    const scroll = add('div', undefined, content);
    scroll.className = 'scroll';
    const table = add('table', undefined, scroll);
    const head = add('tr', undefined, add('thead', undefined, table));
    [
      'Condition',
      'Mean rate Δ',
      'Seed range',
      'Tail Δ',
      'Tail seed range',
    ].forEach((s) => add('th', s, head));
    const body = add('tbody', undefined, table);
    Object.entries(r.comparisons).forEach(([name, d]) => {
      const row = add('tr', undefined, body);
      const a = d.mean_rate_difference,
        b = d.tail_rate_difference;
      [
        name,
        a.mean[g].toFixed(5),
        `${a.min[g].toFixed(5)} … ${a.max[g].toFixed(5)}`,
        b.mean[g].toFixed(5),
        `${b.min[g].toFixed(5)} … ${b.max[g].toFixed(5)}`,
      ].forEach((v) => add('td', v, row));
    });
    plot(
      content,
      c.native_time.difference_trace,
      g,
      r.input_duration_seconds,
      'Difference at the same elapsed time',
    );
    add(
      'p',
      `Native-time difference pattern, leave-one-seed-out similarities: ${c.native_time.leave_one_seed_out_cosine.map((row) => row[g]?.toFixed(3) ?? 'undefined').join(', ')}.`,
      content,
    );
    if (c.same_blocks_different_context) {
      const aligned = c.same_blocks_different_context;
      plot(
        content,
        aligned.difference_trace,
        g,
        r.input_duration_seconds,
        'Identical input blocks in different preceding contexts',
      );
      add(
        'p',
        `Context contrast: RMS mean difference ${aligned.rms_mean_difference[g].toFixed(5)} Hz/neuron; RMS standard error ${aligned.rms_standard_error[g].toFixed(5)}; descriptive ratio ${aligned.descriptive_ratio[g]?.toFixed(2) ?? 'undefined'}. Leave-one-seed-out similarities: ${aligned.leave_one_seed_out_cosine.map((row) => row[g]?.toFixed(3) ?? 'undefined').join(', ')}.`,
        content,
      );
    } else
      add(
        'p',
        'Constant input has no corresponding content blocks; no context realignment is applied.',
        content,
      );
    add(
      'p',
      'Traces show 100 ms rate differences, mean and min/max across seeds. When present, the context plot uses original block positions, not the time when reordered blocks were presented.',
      content,
    );
  }
  group.addEventListener('change', draw);
  condition.addEventListener('change', draw);
  draw();
}
load().catch((error) => {
  root.textContent = error.message;
  root.setAttribute('role', 'alert');
});

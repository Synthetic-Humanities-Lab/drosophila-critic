const $ = (id) => document.getElementById(id);
const base = './experiments/history-v3/';
const primary = 'direct JON postsynaptic partners';
const labels = {
  total: 'B − A during the passage',
  lingering: 'B − A during quiet continuation',
  after_a: 'Passage increment after A',
  after_b: 'Passage increment after B',
  interaction: 'Changed reception: increment after B − increment after A',
};
const n = (value) =>
  Math.abs(value) < 0.00005 ? '0.0000' : Number(value).toFixed(4);
const verdict = (value) => (value ? 'Criterion met' : 'Not met');
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
function render(data) {
  const gap = data.gaps[$('gap').value];
  const pop = gap.populations[$('population').value];
  $('clock').textContent =
    `The shared passage begins ${6 + gap.gap} seconds into the stimulus, after ${gap.gap} seconds of inserted quiet. The first 0.5 seconds is the primary window; the full two-second passage is secondary.`;
  rows(
    'contrasts',
    Object.entries(labels).map(([key, label]) => {
      const p = pop[key],
        m = p.early.mean;
      return [
        label,
        n(m.mean),
        `${m.positive} / ${m.negative} / ${m.zero}`,
        verdict(p.early.temporal.criterion_met),
        verdict(p.full.temporal.criterion_met),
      ];
    }),
  );
  $('manipulation').textContent =
    `First-half-second passage-response checks in this population: after A, ${verdict(pop.after_a.early.temporal.criterion_met).toLowerCase()}; after B, ${verdict(pop.after_b.early.temporal.criterion_met).toLowerCase()}. These check whether adding the passage itself produces a detectable response.`;
  const t = pop.interaction.early.temporal;
  $('criterion-values').textContent =
    `Primary changed-reception test: mean-trace RMS ${n(t.mean_trace_rms)}, variability RMS ${n(t.seed_sd_rms)}, agreement between halves ${n(t.split_half_cosine)}.`;
  const trace = pop.interaction.trace;
  rows(
    'timeline',
    trace.time.map((time, i) => [
      `${time.toFixed(1)}–${(time + 0.1).toFixed(1)}`,
      n(trace.mean[i]),
      `${n(trace.low[i])} to ${n(trace.high[i])}`,
    ]),
  );
  $('audio-links').replaceChildren(
    ...['a_probe', 'b_probe', 'a_quiet', 'b_quiet'].map((key) => {
      const link = document.createElement('a');
      link.href = `${base}g${Math.round(gap.gap * 1000)}_${key}/audio.wav`;
      link.textContent = `${key[0].toUpperCase()} + ${key.endsWith('probe') ? 'passage' : 'quiet'} (WAV)`;
      return link;
    }),
  );
}
try {
  const response = await fetch(`${base}comparison.json`);
  if (!response.ok)
    throw new Error(`Response data unavailable (${response.status})`);
  const data = await response.json();
  $('finding').textContent = data.interpretation.response;
  $('functional').textContent = data.interpretation.functional;
  $('reading').textContent = data.interpretation.reading;
  $('limitation').textContent = data.interpretation.limitation;
  $('controls').textContent =
    `All ${data.controls.length} independently repeated inputs reproduced their complete spike arrays. Probe and quiet trials were also checked for identical spikes up to the passage onset.`;
  rows(
    'overview',
    Object.values(data.gaps).map((g) => {
      const p = g.populations[primary];
      return [
        `${g.gap} seconds`,
        verdict(p.interaction.early.temporal.criterion_met),
        verdict(p.interaction.full.temporal.criterion_met),
        verdict(p.lingering.early.temporal.criterion_met),
      ];
    }),
  );
  for (const [value, label] of Object.keys(data.gaps).map((key) => [
    key,
    `${key} seconds`,
  ])) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    $('gap').append(option);
  }
  for (const group of [
    primary,
    'descending_neuron',
    'JO-A/B input',
    'DNa02',
    'DNp01',
    'MDN',
    'pIP10',
  ]) {
    const option = document.createElement('option');
    option.value = group;
    option.textContent = group;
    $('population').append(option);
  }
  for (const id of ['gap', 'population'])
    $(id).addEventListener('change', () => render(data));
  render(data);
  $('report').hidden = false;
  $('status').hidden = true;
} catch (error) {
  $('status').textContent = `Unable to load this experiment: ${error.message}`;
}

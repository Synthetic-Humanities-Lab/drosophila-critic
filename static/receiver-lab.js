const ns = 'http://www.w3.org/2000/svg';
async function load() {
  const response = await fetch('./experiments/receiver-v2/report.json');
  if (!response.ok)
    throw new Error(`Receiver report unavailable (${response.status})`);
  const report = await response.json();
  const mechanics = report.components.mechanics;
  const passed = Object.values(mechanics.convergence).every(
    (test) => test.pass_2_percent,
  );
  document.querySelector('#convergence').textContent =
    `Velocity (mm/s), 50 ms excerpt after 0.5 s settling. Step-halving at 48/96/192 kHz: ${passed ? 'RMS and peak changes below 2%' : 'criterion not met'}. This tests numerical accuracy, not biological validity.`;
  const samples = report.components.oscillator_plot.map((row) => row[1]);
  const scale = Math.max(...samples.map(Math.abs));
  const path = document.createElementNS(ns, 'path');
  path.setAttribute(
    'd',
    samples
      .map(
        (v, i) =>
          `${i ? 'L' : 'M'}${65 + (i * 815) / (samples.length - 1)},${110 - (v / scale) * 90}`,
      )
      .join(' '),
  );
  path.setAttribute('fill', 'none');
  path.setAttribute('stroke', '#91472f');
  path.setAttribute('stroke-width', '1.6');
  const svg = document.querySelector('#oscillator');
  svg.replaceChildren(path);
  for (const [x, y, label] of [
    [5, 24, scale.toFixed(3)],
    [5, 114, '0'],
    [5, 204, (-scale).toFixed(3)],
    [65, 218, '0.500 s'],
    [825, 218, '0.550 s'],
  ]) {
    const text = document.createElementNS(ns, 'text');
    text.setAttribute('x', x);
    text.setAttribute('y', y);
    text.setAttribute('font-size', '13');
    text.textContent = label;
    svg.append(text);
  }
  const pilot = report.neural_pilot;
  if (!pilot) {
    document.querySelector('#weights').textContent =
      'No neural pilot was run for this report.';
    return;
  }
  const body = document.querySelector('#clocks');
  for (const dt of [0.02, 0.0005, 0.00025]) {
    const rows = pilot.runs.filter(
      (r) => r.configuration.dt_seconds === dt && r.noise_hz === 1.2,
    );
    const silence = rows.find((r) => r.stimulus === 'silence');
    const pulse = rows.find((r) => r.stimulus !== 'silence');
    const tr = document.createElement('tr');
    for (const value of [
      `${dt * 1000} ms`,
      silence?.total_spikes[0]?.toLocaleString() ?? 'Not run',
      pulse?.total_spikes[0]?.toLocaleString() ?? 'Not run',
    ]) {
      const td = document.createElement('td');
      td.textContent = value;
      tr.append(td);
    }
    body.append(tr);
  }
  document.querySelector('#weights').textContent = pilot.weights_unchanged
    ? 'Runtime connectome weights: unchanged, verified by checksum. Noise draws differ across timesteps.'
    : 'Weight verification failed; do not interpret this pilot.';
}
load().catch((error) => {
  document.querySelector('#error').textContent = error.message;
});

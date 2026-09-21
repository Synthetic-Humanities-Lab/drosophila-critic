const ns = 'http://www.w3.org/2000/svg';
async function load() {
  const response = await fetch('./experiments/receiver-v2/report.json', {
    cache: 'no-store',
  });
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

async function loadCalibration() {
  const response = await fetch('./experiments/receiver-v2/calibration.json', {
    cache: 'no-store',
  });
  if (!response.ok)
    throw new Error(`Calibration report unavailable (${response.status})`);
  const data = await response.json();
  function row(id, values) {
    const tr = document.createElement('tr');
    for (const value of values) {
      const td = document.createElement('td');
      td.textContent = value;
      tr.append(td);
    }
    document.getElementById(id).append(tr);
  }
  for (const tone of data.diagnostics.sound_transfer_tones) {
    if ([200, 394, 600].includes(tone.frequency_hz))
      row('sound-tones', [
        `${tone.frequency_hz} Hz`,
        `${tone.air_velocity_rms_mm_s.toFixed(2)} mm/s`,
        `${tone.displacement_rms_nm.toFixed(1)} nm`,
      ]);
  }
  for (const [name, r] of Object.entries(data.recordings))
    row('mechanical-recordings', [
      name === 'reference' ? 'Synthetic reference' : 'Human performance',
      r.air_rms_mm_s.toFixed(5),
      r.displacement_rms_nm.toFixed(2),
      r.velocity_rms_mm_s.toFixed(5),
    ]);
  document.querySelector('#calibration-range').textContent =
    `The source measurement covered 100–1500 Hz. Audio energy outside that band: synthetic ${(100 * data.recordings.reference.fraction_audio_energy_outside_source_100_1500_hz).toFixed(1)}%; human ${(100 * data.recordings.human.fraction_audio_energy_outside_source_100_1500_hz).toFixed(1)}%. Out-of-band and arbitrary-level predictions are extrapolations.`;
  for (const tone of data.diagnostics.force_transduction_tones) {
    if (tone.force_peak_pn === 1)
      row('channel-tones', [
        `${tone.frequency_hz} Hz`,
        tone.mean_excess_open_probability.toFixed(4),
      ]);
  }
  const bridge = data.constant_force_bridge_audit;
  if (bridge) {
    const best = Math.min(
      ...bridge.fits.map((fit) => fit.normalized_complex_response_error),
    );
    document.querySelector('#bridge-audit').textContent =
      `Attempted air-to-force connection: a fitted constant gain leaves at least ${(100 * best).toFixed(1)}% normalized error between these source models in the linear-response comparison. This cross-study check does not invalidate either model. No fitted gain was applied to the poems.`;
  } else {
    document.querySelector('#bridge-audit').textContent =
      'Bridge comparison unavailable in this report.';
  }
  const discrepant = data.parameter_audit.fits
    .filter((r) => !r.motor_time_within_5_percent)
    .map((r) => r.parameters.fly);
  document.querySelector('#source-audit').textContent =
    `Source-table audit: motor relaxation times for fits ${discrepant.join(' and ')} do not reconcile with their printed parameters. No silent correction was applied. These force diagnostics use fit ${data.parameter_audit.selected_fit}, with consistent time constants. Channels are not connectome neuron identities.`;
}
loadCalibration().catch((error) => {
  document.querySelector('#calibration-error').textContent = error.message;
});

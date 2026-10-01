function roundEven(x) {
  const lo = Math.floor(x),
    fraction = x - lo;
  return fraction === 0.5 ? (lo % 2 === 0 ? lo : lo + 1) : Math.round(x);
}
// Waveforms only. Same linear level matching and source-reference mechanics as Python.
export function levelMatch(a, b) {
  const stats = (x) => {
    let sum = 0,
      peak = 0;
    for (const v of x) {
      if (!Number.isFinite(v) || Math.abs(v) > 1)
        throw new Error('Audio samples exceed the supported range.');
      sum += v * v;
      peak = Math.max(peak, Math.abs(v));
    }
    const rms = Math.sqrt(sum / x.length);
    if (!rms) throw new Error('This recording is silent.');
    return { rms, peak };
  };
  const sa = stats(a),
    sb = stats(b),
    target = Math.min(
      0.05,
      (0.95 * sa.rms) / sa.peak,
      (0.95 * sb.rms) / sb.peak,
    );
  const convert = (x, s) => {
    const out = new Float64Array(x.length);
    for (let i = 0; i < x.length; i++)
      out[i] = roundEven(((x[i] * target) / s.rms) * 32767) / 32768;
    return out;
  };
  return {
    a: convert(a, sa),
    b: convert(b, sb),
    target,
    gains: [target / sa.rms, target / sb.rms],
  };
}
export function mechanicalInput(samples, config) {
  const frames =
      Math.ceil(samples.length / config.frame_samples) + config.decay_frames,
    result = new Float64Array(frames);
  let x = 0,
    v = 0;
  const A = config.transition,
    B = config.forcing;
  for (let frame = 0; frame < frames; frame++) {
    let square = 0;
    for (let j = 0; j < config.frame_samples; j++) {
      const i = frame * config.frame_samples + j;
      const air =
        (i < samples.length ? samples[i] : 0) * config.air_velocity_gain;
      square += x * x;
      const nx = A[0][0] * x + A[0][1] * v + B[0] * air;
      v = A[1][0] * x + A[1][1] * v + B[1] * air;
      x = nx;
    }
    result[frame] = Math.min(
      config.cap,
      (Math.sqrt(square / config.frame_samples) / config.reference_nm) * 0.4,
    );
  }
  return Array.from(result);
}
export function mono(buffer) {
  if (buffer.sampleRate !== 48000)
    throw new Error('This browser cannot decode at the required 48 kHz rate.');
  if (buffer.duration < 1 || buffer.duration > 60)
    throw new Error('Choose a recording between 1 and 60 seconds.');
  const data = new Float64Array(buffer.length);
  for (let c = 0; c < buffer.numberOfChannels; c++) {
    const channel = buffer.getChannelData(c);
    for (let i = 0; i < data.length; i++)
      data[i] += channel[i] / buffer.numberOfChannels;
  }
  return data;
}
export function summarize(sound, silence, before, soundFrames) {
  const group = 1,
    rates = sound.group_counts.map(
      (r, i) =>
        (r[group] - silence.group_counts[i][group]) /
        sound.group_sizes[group] /
        0.02,
    );
  const average = (x) => x.reduce((a, b) => a + b, 0) / x.length;
  return {
    mean: average(rates.slice(before, before + soundFrames)),
    tail: average(rates.slice(before + soundFrames)),
    rates,
  };
}
export function localReading(a, b) {
  const delta = b.mean - a.mean;
  if (Math.abs(delta) < 1e-9)
    return 'These two single-run measurements give the same mean downstream change. This receiver offers no basis for a distinction in their average activity.';
  return `Your delivery leaves ${delta > 0 ? 'more' : 'less'} mean activity downstream of the auditory input than the synthetic reference. Read as an encounter, the pattern of delivery changes how this apparatus is disturbed. This is one seeded comparison, not a reliable difference across repetitions or a report of the fly’s feelings.`;
}

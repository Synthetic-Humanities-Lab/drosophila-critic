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
        throw new Error("Audio samples exceed the supported range.");
      sum += v * v;
      peak = Math.max(peak, Math.abs(v));
    }
    const rms = Math.sqrt(sum / x.length);
    if (!rms) throw new Error("This recording is silent.");
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
export function mechanicalEncoding(samples, config) {
  const frames =
      Math.ceil(samples.length / config.frame_samples) + config.decay_frames,
    result = new Float64Array(frames),
    displacement = [],
    waveform = [];
  let x = 0,
    v = 0;
  const A = config.transition,
    B = config.forcing;
  for (let frame = 0; frame < frames; frame++) {
    let square = 0,
      acoustic = 0;
    for (let j = 0; j < config.frame_samples; j++) {
      const i = frame * config.frame_samples + j;
      const air =
        (i < samples.length ? samples[i] : 0) * config.air_velocity_gain;
      if (i < samples.length) acoustic += samples[i] * samples[i];
      square += x * x;
      const nx = A[0][0] * x + A[0][1] * v + B[0] * air;
      v = A[1][0] * x + A[1][1] * v + B[1] * air;
      x = nx;
    }
    displacement.push(Math.sqrt(square / config.frame_samples));
    waveform.push(Math.sqrt(acoustic / config.frame_samples));
    result[frame] = Math.min(
      config.cap,
      (Math.sqrt(square / config.frame_samples) / config.reference_nm) * 0.4,
    );
  }
  return {
    frame_seconds: config.frame_samples / config.sample_rate,
    injection: Array.from(result),
    displacement_nm: displacement,
    waveform_rms: waveform,
  };
}
export function mechanicalInput(samples, config) {
  return mechanicalEncoding(samples, config).injection;
}
export function normalizeRecording(samples) {
  let sum = 0,
    peak = 0;
  for (const x of samples) {
    if (!Number.isFinite(x) || Math.abs(x) > 1)
      throw new Error("Audio samples exceed the supported range.");
    sum += x * x;
    peak = Math.max(peak, Math.abs(x));
  }
  if (!samples.length) throw new Error("The recording is empty.");
  const rms = Math.sqrt(sum / samples.length);
  const target = rms ? Math.min(0.05, (0.95 * rms) / peak) : 0;
  const gain = rms ? target / rms : 1;
  const processed = Float64Array.from(
    samples,
    (x) => roundEven(x * gain * 32767) / 32768,
  );
  let outputSquare = 0,
    outputPeak = 0;
  for (const x of processed) {
    outputSquare += x * x;
    outputPeak = Math.max(outputPeak, Math.abs(x));
  }
  return {
    samples: processed,
    metadata: {
      requested_rms: 0.05,
      target_rms: target,
      input_rms: rms,
      input_peak: peak,
      gain,
      output_rms: Math.sqrt(outputSquare / processed.length),
      output_peak: outputPeak,
      sample_count: processed.length,
      silent: rms === 0,
      peak_ceiling: 0.95,
      method: "linear gain; 16-bit PCM rounding; no compression",
    },
  };
}
export function mono(buffer) {
  if (buffer.sampleRate !== 48000)
    throw new Error("This browser cannot decode at the required 48 kHz rate.");
  if (buffer.duration < 1 || buffer.duration > 60)
    throw new Error("Choose a recording between 1 and 60 seconds.");
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
    return "These two single-run measurements give the same mean downstream change. This receiver offers no basis for a distinction in their average activity.";
  return `Your delivery leaves ${delta > 0 ? "more" : "less"} mean activity downstream of the auditory input than the synthetic reference. Read as an encounter, the pattern of delivery changes how this apparatus is disturbed. This is one seeded comparison, not a reliable difference across repetitions or a report of the fly’s feelings.`;
}

export const GROUP_IDS = [
  "global",
  "JO-A/B input",
  "direct JON postsynaptic partners",
  "descending_neuron",
  "wing motor (flytalk WING_MN)",
];
export function timeLabel(time) {
  const t = Math.max(0, Math.floor(time));
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
}
export function binAt(record, time) {
  return Math.max(
    0,
    Math.min(
      record.activity.sound.mean.length - 1,
      Math.floor((time - record.start_time) / record.bin_seconds),
    ),
  );
}
function average(values) {
  return values.reduce((a, b) => a + b, 0) / values.length;
}
function single(value) {
  return { mean: value, minimum: value, maximum: value };
}
export function visitorPlayback(
  sound,
  silence,
  model,
  duration,
  input,
  normalization,
) {
  if (sound.counts.length !== silence.counts.length)
    throw new Error("The silence control has a different duration.");
  const rates = (run) =>
    run.counts.map((n, i) =>
      GROUP_IDS.map((name) => {
        if (name === "global") return n / model.neurons / 0.02;
        const g = run.group_names.indexOf(name);
        if (g < 0 || !run.group_sizes[g])
          throw new Error(`Missing neural population: ${name}`);
        return run.group_counts[i][g] / run.group_sizes[g] / 0.02;
      }),
    );
  const a = rates(sound),
    b = rates(silence),
    d = a.map((r, i) => r.map((x, g) => x - b[i][g]));
  const activity = {};
  for (const [key, rows] of Object.entries({
    sound: a,
    silence: b,
    change: d,
  })) {
    const mean = [];
    for (let i = 0; i < rows.length; i += 5)
      mean.push(
        GROUP_IDS.map((_, g) => average(rows.slice(i, i + 5).map((r) => r[g]))),
      );
    activity[key] = { mean, minimum: mean, maximum: mean };
  }
  const end = 75 + Math.ceil(duration / 0.02);
  return {
    schema_version: "fly-playback-v2",
    id: "visitor",
    audio_duration: duration,
    playback_duration: a.length * 0.02 - 1.5,
    start_time: -1.5,
    bin_seconds: 0.1,
    seeds: [sound.seed],
    activity,
    input,
    normalization,
    summary: GROUP_IDS.map((id, g) => ({
      id,
      sound: single(average(a.slice(75, end).map((r) => r[g]))),
      silence: single(average(b.slice(75, end).map((r) => r[g]))),
      change: single(average(d.slice(75, end).map((r) => r[g]))),
      after_change: single(average(d.slice(end).map((r) => r[g]))),
    })),
    body: { available: false, reason: "No qualified neural-to-body coupling" },
  };
}
export function responseExplanation(summary, repetitions, silence = false) {
  if (silence)
    return "This is the same model with no sound input. Its nerve cells still fire. Use this to see which activity also occurs without the reading.";
  const change = summary.change.mean;
  if (Math.abs(change) < 1e-9)
    return "Average activity in these cells was the same as in silence. Individual moments can still be compared in the trace.";
  const consistent = summary.change.minimum > 0 || summary.change.maximum < 0;
  const percent =
    summary.silence.mean > 0
      ? Math.abs((change / summary.silence.mean) * 100)
      : null;
  const amount =
    percent !== null
      ? `${percent < 0.1 ? "less than 0.1" : percent.toFixed(1)}% `
      : "";
  return (
    `These cells fired ${amount}${change > 0 ? "more" : "less"} often during the reading than in silence. ` +
    (repetitions === 1
      ? "This is one simulation, so we have not checked how consistent the change is."
      : consistent
        ? `All ${repetitions} repeated runs showed this direction of change.`
        : "The repeated runs did not all show the same direction of change.")
  );
}

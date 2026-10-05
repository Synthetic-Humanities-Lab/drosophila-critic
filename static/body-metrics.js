// Recomputed for the requested interval, including when using a saved silence prefix.
export function bodyMetrics(body, root, baseline, duration) {
  let distance = 0,
    flying = 0,
    turns = 0,
    after = 0,
    inverted = 0;
  const heading = (q) =>
    Math.atan2(
      2 * (q[0] * q[3] + q[1] * q[2]),
      1 - 2 * (q[2] ** 2 + q[3] ** 2),
    );
  for (let i = 0; i < body.positions.length; i++) {
    if (body.airborne[i]) flying += 0.02;
    if (body.inverted[i]) inverted += 0.02;
    if (!i) continue;
    const p = body.positions[i][root],
      old = body.positions[i - 1][root];
    const d = Math.hypot(p[0] - old[0], p[1] - old[1]);
    if (!body.airborne[i]) distance += d;
    if (i * 0.02 >= baseline + duration) after += d;
    const angle =
      heading(body.quaternions[i][root]) -
      heading(body.quaternions[i - 1][root]);
    turns +=
      Math.abs(Math.atan2(Math.sin(angle), Math.cos(angle))) / (2 * Math.PI);
  }
  return {
    distance_walked_cm: distance,
    flight_seconds: flying,
    turns_revolutions: turns,
    after_voice_distance_cm: after,
    boundary_seconds: body.commands.filter((c) => c.boundary).length * 0.02,
    inverted_seconds: inverted,
    complete: true,
    failures: [],
  };
}

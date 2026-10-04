// Display-only tracking. The recorded body and neural timelines are untouched.
const WINDOW_SECONDS = 0.3;
const SIGMA_SECONDS = 0.1;
const MAX_OFFSET_CM = 0.24;

export function closeView(target) {
  const lookAt = [target[0], target[2], -target[1]];
  return {
    lookAt,
    position: lookAt.map((value, axis) => value + [0.55, 0.625, 1.3125][axis]),
    fov: 38,
  };
}

export function frameAt(times, time) {
  if (time <= times[0]) return { lo: 0, hi: 0, alpha: 0 };
  const last = times.length - 1;
  if (time >= times[last]) return { lo: last, hi: last, alpha: 0 };
  let lo = 0,
    hi = last;
  while (lo + 1 < hi) {
    const mid = (lo + hi) >> 1;
    if (times[mid] <= time) lo = mid;
    else hi = mid;
  }
  return { lo, hi, alpha: (time - times[lo]) / (times[hi] - times[lo]) };
}

export function interpolatePosition(positions, { lo, hi, alpha }) {
  return positions[lo].map(
    (value, axis) => value + (positions[hi][axis] - value) * alpha,
  );
}

function smoothPosition(positions, times, { lo, hi, alpha: t }) {
  if (lo === hi) return [...positions[lo]];
  const before = Math.max(0, lo - 1);
  const after = Math.min(times.length - 1, hi + 1);
  const dt = times[hi] - times[lo];
  return positions[lo].map((value, axis) => {
    const a =
      (positions[hi][axis] - positions[before][axis]) /
      (times[hi] - times[before]);
    const b = (positions[after][axis] - value) / (times[after] - times[lo]);
    return (
      (2 * t ** 3 - 3 * t ** 2 + 1) * value +
      (t ** 3 - 2 * t ** 2 + t) * dt * a +
      (-2 * t ** 3 + 3 * t ** 2) * positions[hi][axis] +
      (t ** 3 - t ** 2) * dt * b
    );
  });
}

export class FollowCameraTrack {
  constructor(recording, rootIndex) {
    this.times = recording.time;
    this.positions = recording.positions.map((row) => row[rootIndex]);
    let start = 0;
    this.centres = this.positions.map((position, i) => {
      const time = this.times[i];
      while (this.times[start] < time - WINDOW_SECONDS - 1e-9) start++;
      const centre = [0, 0, 0];
      let total = 0;
      for (
        let j = start;
        j < this.times.length && this.times[j] <= time + WINDOW_SECONDS + 1e-9;
        j++
      ) {
        const weight = Math.exp(
          -0.5 * ((this.times[j] - time) / SIGMA_SECONDS) ** 2,
        );
        total += weight;
        for (let axis = 0; axis < 3; axis++)
          centre[axis] += this.positions[j][axis] * weight;
      }
      return centre.map((value) => value / total);
    });
  }

  sample(time) {
    const frame = frameAt(this.times, time);
    const position = interpolatePosition(this.positions, frame);
    const centre = smoothPosition(this.centres, this.times, frame);
    // Keep fast turns inside the close frame without tying the view to body yaw.
    const offset = centre.map((value, axis) => value - position[axis]);
    const distance = Math.hypot(...offset);
    const factor = distance
      ? (MAX_OFFSET_CM * Math.tanh(distance / MAX_OFFSET_CM)) / distance
      : 1;
    const target = position.map((value, axis) => value + offset[axis] * factor);
    return { frame, position, target };
  }
}

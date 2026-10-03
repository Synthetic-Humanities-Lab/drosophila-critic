// Display-only tracking. The recorded body and neural timelines are untouched.
const WINDOW_SECONDS = 0.18;
const SIGMA_SECONDS = 0.06;
const MAX_OFFSET_CM = 0.12;

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
    const centre = interpolatePosition(this.centres, frame);
    // Keep fast turns inside the close frame without tying the view to body yaw.
    const offset = centre.map((value, axis) => value - position[axis]);
    const factor = Math.min(1, MAX_OFFSET_CM / (Math.hypot(...offset) || 1));
    const target = position.map((value, axis) => value + offset[axis] * factor);
    return { frame, position, target };
  }
}

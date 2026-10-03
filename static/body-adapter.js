// Must agree with critic/body_adapter.py. Versioned parameters are data, not UI settings.
export class NeuralBodyAdapter {
  constructor(config) {
    this.c = config;
    this.r = {};
    this.armed = true;
    for (const key of [
      "walk",
      "turn_left",
      "turn_right",
      "takeoff",
      "flight",
      "flight_left",
      "flight_right",
    ])
      this.r[`motor_${key}`] = 0;
  }
  step(input) {
    const c = this.c,
      r = this.r,
      alpha = -Math.expm1(-c.dt / c.smoothing_seconds);
    for (const key in r) {
      if (!Number.isFinite(input[key]) || input[key] < 0)
        throw new Error(`Invalid firing rate: ${key}`);
      r[key] += alpha * (input[key] - r[key]);
    }
    const takeoff = this.armed && r.motor_takeoff >= c.takeoff_threshold_hz;
    if (takeoff) this.armed = false;
    else if (r.motor_takeoff < c.takeoff_rearm_hz) this.armed = true;
    return {
      walk_speed: Math.min(
        c.maximum_walking_cm_s,
        c.walking_gain_cm_s_per_hz * r.motor_walk,
      ),
      walk_turn: clamp(
        c.walking_turn_gain_rad_s_per_hz *
          (r.motor_turn_left - r.motor_turn_right),
        -c.maximum_walking_turn_rad_s,
        c.maximum_walking_turn_rad_s,
      ),
      takeoff,
      flight_speed: Math.min(
        c.maximum_flight_cm_s,
        c.flight_base_cm_s + c.flight_gain_cm_s_per_hz * r.motor_flight,
      ),
      flight_turn: clamp(
        c.flight_turn_gain_rad_s_per_hz *
          (r.motor_flight_left - r.motor_flight_right),
        -c.maximum_flight_turn_rad_s,
        c.maximum_flight_turn_rad_s,
      ),
      flight_activity: r.motor_flight,
    };
  }
}
export const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const wrap = (x) => Math.atan2(Math.sin(x), Math.cos(x));
export class BodySupervisor {
  constructor(config) {
    this.c = config;
    this.state = "standing";
    this.since = 0;
    this.lastLaunch = -config.takeoff_refractory_seconds;
    this.low = 0;
    this.boundary = false;
    this.events = [];
    this.pendingLaunch = false;
  }
  transition(state, time, reason) {
    if (state === this.state) return;
    this.events.push({
      time,
      from: this.state,
      to: state,
      reason,
      source: "engineering supervisor",
    });
    this.state = state;
    this.since = time;
  }
  command(neural, { time, dt, position, yaw, landed = false }) {
    const c = this.c;
    if (["standing", "walking"].includes(this.state)) {
      this.transition(
        this.pendingLaunch ||
          neural.walk_speed > 0.05 ||
          Math.abs(neural.walk_turn) > 0.05
          ? "walking"
          : "standing",
        time,
        "walking command",
      );
      this.pendingLaunch ||=
        neural.takeoff &&
        time - this.lastLaunch >= c.takeoff_refractory_seconds;
      if (this.pendingLaunch)
        this.transition("walking", time, "move inward before takeoff");
      if (
        this.pendingLaunch &&
        Math.abs(position[0]) < 3 &&
        Math.abs(position[1]) < 2
      ) {
        this.transition("takeoff", time, "DNp01 threshold");
        this.lastLaunch = time;
        this.low = 0;
        this.pendingLaunch = false;
      }
    } else if (
      this.state === "takeoff" &&
      time - this.since >= 0.8 &&
      position[2] > 0.25
    ) {
      this.transition(
        "flight",
        time,
        "wing deployment complete and body airborne",
      );
    } else if (this.state === "flight") {
      if (neural.flight_activity < c.flight_end_hz) this.low += dt;
      else if (neural.flight_activity > c.flight_resume_hz) this.low = 0;
      if (
        time - this.since > c.minimum_flight_seconds &&
        this.low >= c.landing_delay_seconds
      )
        this.transition("landing", time, "low DLM drive after minimum flight");
    } else if (this.state === "landing" && landed) {
      this.transition(
        "walking",
        time,
        "feet reached floor; walking policy resumed",
      );
    }
    const air = ["takeoff", "flight", "landing"].includes(this.state);
    let speed = air ? neural.flight_speed : neural.walk_speed,
      turn = air ? neural.flight_turn : neural.walk_turn;
    if (this.state === "takeoff") {
      speed = 8;
      turn = 0;
    } else if (this.state === "landing") {
      speed = 1;
      turn = 0;
    }
    const requested = { speed, turn },
      lookahead = air ? 0.45 : 0.3;
    const predicted = [
      position[0] + speed * Math.cos(yaw) * lookahead,
      position[1] + speed * Math.sin(yaw) * lookahead,
    ];
    const boundary =
      this.pendingLaunch ||
      (this.state !== "takeoff" &&
        (Math.abs(predicted[0]) > 7 ||
          Math.abs(predicted[1]) > 5 ||
          Math.abs(position[0]) > 8 ||
          Math.abs(position[1]) > 6));
    if (boundary) {
      const limit = air ? 5 : 1.5;
      turn = clamp(
        4 * wrap(Math.atan2(-position[1], -position[0]) - yaw),
        -limit,
        limit,
      );
      speed = this.pendingLaunch ? 0.75 : Math.min(speed, air ? 6 : 0.75);
    }
    if (boundary !== this.boundary) {
      this.events.push({
        time,
        source: "arena confinement",
        active: boundary,
        requested,
        applied: { speed, turn },
      });
      this.boundary = boundary;
    }
    return {
      state: this.state,
      speed,
      turn,
      height: c.flight_height_cm,
      boundary,
      requested,
    };
  }
}

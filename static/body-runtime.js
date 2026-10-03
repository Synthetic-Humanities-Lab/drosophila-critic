import { WingPattern } from "./body-policy.js";
import { clamp } from "./body-adapter.js";

export function quatMultiply(a, b) {
  const [w, x, y, z] = a,
    [v, i, j, k] = b;
  return [
    w * v - x * i - y * j - z * k,
    w * i + x * v + y * k - z * j,
    w * j - x * k + y * v + z * i,
    w * k + x * j - y * i + z * v,
  ];
}
export function orientation(yaw, pitch = 0) {
  return quatMultiply(
    [Math.cos(yaw / 2), 0, 0, Math.sin(yaw / 2)],
    [Math.cos(pitch / 2), 0, Math.sin(pitch / 2), 0],
  );
}
const gather = (source, indices) => indices.map((i) => source[i]);

// Single-threaded official MuJoCo, in a worker. Every transform comes from mj_step.
export class BodyRuntime {
  constructor(mj, assets, policies) {
    this.mj = mj;
    this.assets = assets;
    this.policies = policies;
    this.m = mj.MjModel.from_xml_string(assets.xml);
    this.d = new mj.MjData(this.m);
    const { m, d } = this;
    d.qpos.set(assets.model.qpos);
    d.qvel.set(assets.model.qvel);
    d.act.set(assets.model.act);
    mj.mj_forward(m, d);
    this.stance = Array.from(d.qpos);
    this.v = assets.views;
    this.root = this.v.root;
    this.wpg = new WingPattern(assets.wingbeat);
    this.sensors = Array.from(d.sensordata);
    this.target = Array.from(d.xpos.slice(this.root * 3, this.root * 3 + 3));
    this.heading = 0;
    this.phase = "walking";
    this.phaseTime = 0;
    this.blend = 0;
    this.landed = false;
    this.contacts = 0;
    this.events = [];
    this.commandSpeed = 0;
    this.commandTurn = 0;
    this.entryPose = Array.from(d.qpos);
  }
  get time() {
    return this.d.time;
  }
  get position() {
    return this.d.xpos.slice(this.root * 3, this.root * 3 + 3);
  }
  get yaw() {
    return Math.atan2(
      this.d.xmat[this.root * 9 + 3],
      this.d.xmat[this.root * 9],
    );
  }
  observation(kind, speed, turn, height, pitch) {
    const d = this.d,
      view = this.v.views[kind],
      matrix = d.xmat.slice(this.root * 9, this.root * 9 + 9),
      root = this.position;
    const local = (pos) =>
      [0, 1, 2].map((j) =>
        pos.reduce((s, x, k) => s + x * matrix[k * 3 + j], 0),
      );
    const result = {
      "walker/joints_pos": gather(d.qpos, view.qpos),
      "walker/joints_vel": gather(d.qvel, view.qvel),
      "walker/actuator_activation": gather(d.act, view.act),
      "walker/world_zaxis": Array.from(matrix.slice(6, 9)),
    };
    for (const [key, ids] of Object.entries(view.sensors))
      if (view.info.observations[`walker/${key}`])
        result[`walker/${key}`] = gather(this.sensors, ids);
    if (kind === "walking")
      result["walker/appendages_pos"] = view.sites.flatMap((i) =>
        local([0, 1, 2].map((j) => d.site_xpos[3 * i + j] - root[j])),
      );
    const count = kind === "walking" ? 65 : 6,
      dt = kind === "walking" ? 0.002 : 0.0002;
    const refs = [],
      rotations = [],
      pos = [...this.target];
    let yaw = this.heading;
    const q = d.xquat.slice(this.root * 4, this.root * 4 + 4),
      inverse = [q[0], -q[1], -q[2], -q[3]];
    for (let i = 0; i < count; i++) {
      pos[2] = height;
      refs.push(...local(pos.map((x, k) => x - root[k])));
      const relative = quatMultiply(inverse, orientation(yaw, pitch));
      rotations.push(...relative.map((x) => (relative[0] < 0 ? -x : x)));
      yaw += turn * dt;
      pos[0] += speed * dt * Math.cos(yaw);
      pos[1] += speed * dt * Math.sin(yaw);
    }
    result["walker/ref_displacement"] = refs;
    result["walker/ref_root_quat"] = rotations;
    return result;
  }
  step({ speed = 2, turn = 0, state = "walking", height = 2 }) {
    const { m, d, mj } = this,
      root = this.position;
    if (state === "landing") {
      this.contacts = this.v.views.walking.sites
        .slice(0, 6)
        .filter((i) => d.site_xpos[3 * i + 2] < 0.025).length;
      if (d.ncon > 0 && root[2] < 0.24 && this.contacts >= 2)
        this.landed = true;
      if (this.landed) state = "walking";
    } else if (state === "takeoff") this.landed = false;
    if (state !== this.phase) {
      this.events.push({
        time: d.time,
        from: this.phase,
        to: state,
        source: "body-controller handover",
        contacts: this.contacts,
      });
      this.phase = state;
      this.phaseTime = 0;
      this.target = Array.from(root);
      this.heading = this.yaw;
      this.entryPose = Array.from(d.qpos);
      if (state === "takeoff") this.wpg.reset();
    }
    const preparing = state === "takeoff" && this.phaseTime < 0.3 - 1e-8;
    const airborne =
      ["takeoff", "flight", "landing"].includes(state) && !preparing;
    if (preparing) {
      speed = 0;
      turn = 0;
    }
    const dt = airborne ? 0.0002 : 0.002,
      kind = airborne ? "flight" : "walking";
    if (!airborne) {
      turn = clamp(turn, -1.5, 1.5);
      if (Math.abs(turn) > 0.05 && !preparing) {
        speed = Math.max(speed, 2);
        turn = clamp(turn, -speed, speed);
      }
    }
    this.commandSpeed += clamp(speed - this.commandSpeed, -dt * 50, dt * 50);
    this.commandTurn += clamp(turn - this.commandTurn, -dt * 10, dt * 10);
    speed = this.commandSpeed;
    turn = this.commandTurn;
    m.opt.timestep = 0.00005;
    this.phaseTime += dt;
    this.blend += clamp((airborne ? 1 : 0) - this.blend, -dt / 0.25, dt / 0.15);
    const pitch = ((-47.5 * Math.PI) / 180) * this.blend,
      goal = airborne && state !== "landing" ? height : 0.1278;
    this.target[2] += clamp(goal - this.target[2], -dt * 1.5, dt * 5);
    this.heading += turn * dt;
    this.target[0] += speed * dt * Math.cos(this.heading);
    this.target[1] += speed * dt * Math.sin(this.heading);
    if (airborne) {
      const error = this.target.map((x, i) => x - root[i]),
        length = Math.hypot(...error);
      if (length > 0.15)
        this.target = error.map((x, i) => root[i] + (x * 0.15) / length);
    }
    const action =
      preparing || state === "standing"
        ? new Float32Array(this.v.views[kind].actions.length)
        : this.policies[kind].infer(
            this.observation(kind, speed, turn, this.target[2], pitch),
          );
    if (!action.every(Number.isFinite))
      throw new Error("Body policy returned a non-finite command.");
    d.ctrl.fill(0);
    const view = this.v.views[kind];
    if (airborne) {
      const pattern =
        state === "takeoff" && this.phaseTime < 0.4
          ? this.assets.wingbeat.patterns[this.wpg.frequencyIndex].traj[
              this.wpg.index
            ]
          : this.wpg.step(218 * (1 + 0.05 * action.at(-1)));
      for (let j = 0; j < 6; j++)
        action[j + 3] += pattern[j] - d.qpos[this.v.wing_q[j]];
      view.actions.forEach((a, i) => (d.ctrl[a] = action[i]));
      if (state === "takeoff") {
        const gain = clamp((this.phaseTime - 0.4) / 0.05, 0, 1),
          rest = this.assets.wingbeat.patterns[100].traj[0];
        this.v.wings.forEach(
          (a, i) =>
            (d.ctrl[a] =
              gain * d.ctrl[a] +
              (1 - gain) * 0.15 * (rest[i] - d.qpos[this.v.wing_q[i]])),
        );
      }
      const extension =
        state === "landing"
          ? clamp((0.8 - root[2]) / 0.5, 0, 1)
          : +(state === "takeoff");
      for (const [a, q] of this.v.leg_actuators)
        d.ctrl[a] =
          (1 - extension) * this.v.qpos_spring[q] + extension * this.stance[q];
    } else {
      view.actions.forEach((a, i) => (d.ctrl[a] = action[i]));
      this.v.wings.forEach(
        (a, i) =>
          (d.ctrl[a] =
            0.002 *
            (this.v.qpos_spring[this.v.wing_q[i]] - d.qpos[this.v.wing_q[i]])),
      );
      if (preparing || state === "standing") {
        d.ctrl.fill(0);
        this.v.wings.forEach(
          (a, i) =>
            (d.ctrl[a] =
              0.002 *
              (this.v.qpos_spring[this.v.wing_q[i]] -
                d.qpos[this.v.wing_q[i]])),
        );
        const blend = Math.min(1, this.phaseTime / 0.15);
        for (const [a, q] of this.v.leg_actuators)
          d.ctrl[a] = (1 - blend) * this.entryPose[q] + blend * this.stance[q];
        for (const a of view.actions.slice(0, 6)) d.ctrl[a] = 0;
      }
    }
    const n = Math.round(dt / m.opt.timestep),
      sensors = new Float64Array(d.sensordata.length);
    for (let i = 0; i < n; i++) {
      mj.mj_step(m, d);
      const s = d.sensordata;
      for (let j = 0; j < s.length; j++) sensors[j] += s[j];
    }
    this.sensors = Array.from(sensors, (x) => x / n);
    mj.mj_forward(m, d);
    if (!d.qpos.every(Number.isFinite) || d.qvel.some((x) => Math.abs(x) > 1e6))
      throw new Error("Body physics became unstable.");
    return dt;
  }
  snapshot() {
    const chunk = (a, n) =>
      Array.from({ length: a.length / n }, (_, i) =>
        Array.from(a.slice(i * n, (i + 1) * n)),
      );
    return {
      time: this.d.time,
      positions: chunk(this.d.xpos, 3),
      quaternions: chunk(this.d.xquat, 4),
      state: this.phase,
      airborne:
        this.position[2] > 0.25 &&
        this.v.views.walking.sites
          .slice(0, 6)
          .every((i) => this.d.site_xpos[3 * i + 2] > 0.025),
    };
  }
  dispose() {
    this.d.delete();
    this.m.delete();
  }
}

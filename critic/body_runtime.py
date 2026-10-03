"""Local reference runtime for the combined, actuated flybody.

Commands and transitions are engineering additions. This module does not alter
the connectome, read audio, or receive poem text.
"""

import json
from pathlib import Path

import mujoco
import numpy as np

from critic.body_policy import FrozenBodyPolicy


def quat_mul(a, b):
    w, x, y, z = a
    v, i, j, k = b
    return np.array(
        [
            w * v - x * i - y * j - z * k,
            w * i + x * v + y * k - z * j,
            w * j - x * k + y * v + z * i,
            w * k + x * j - y * i + z * v,
        ]
    )


def orientation(yaw, pitch=0):
    return quat_mul(
        [np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)], [np.cos(pitch / 2), 0, np.sin(pitch / 2), 0]
    )


class BodyRuntime:
    def __init__(self, directory="results/body-controller/export"):
        from flybody.tasks.pattern_generators import WingBeatPatternGenerator

        self.directory = Path(directory)
        self.model = m = mujoco.MjModel.from_xml_path(str(self.directory / "body.xml"))
        self.data = d = mujoco.MjData(m)
        with np.load(self.directory / "initial.npz") as initial:
            d.qpos[:], d.qvel[:], d.act[:] = initial["qpos"], initial["qvel"], initial["act"]
        mujoco.mj_forward(m, d)
        self.stance = d.qpos.copy()
        self.policies = {
            k: FrozenBodyPolicy.load(self.directory / f"{k}.npz") for k in ["walking", "flight"]
        }
        self.views = {}
        for kind in self.policies:
            info = json.loads((self.directory / f"{kind}-observation.json").read_text())
            ids = [self.id("joint", n) for n in info["joints"]]
            actions = [
                self.id("actuator", "walker/" + n) for n in info["action_names"] if n != "user_0"
            ]
            acts = [int(m.actuator_actadr[self.id("actuator", n)]) for n in info["actuators"]]
            self.views[kind] = {
                "info": info,
                "qpos": m.jnt_qposadr[ids],
                "qvel": m.jnt_dofadr[ids],
                "actions": actions,
                "act": acts if kind == "walking" else [],
                "sites": [self.id("site", n) for n in info["appendages"]],
            }
            self.views[kind]["sensors"] = {
                k: np.concatenate(
                    [
                        np.arange(m.sensor_adr[s], m.sensor_adr[s] + m.sensor_dim[s])
                        for s in [self.id("sensor", n) for n in names]
                    ]
                ).astype(int)
                for k, names in info["sensors"].items()
                if names
            }
        self.root = self.id("body", "walker/thorax")
        self.wings = np.array(
            [
                self.id("actuator", "walker/wing_" + axis + "_" + side)
                for side in ["left", "right"]
                for axis in ["yaw", "roll", "pitch"]
            ]
        )
        self.wing_q = np.array(
            [
                m.jnt_qposadr[self.id("joint", "walker/wing_" + axis + "_" + side)]
                for side in ["left", "right"]
                for axis in ["yaw", "roll", "pitch"]
            ]
        )
        self.wpg = WingBeatPatternGenerator(
            base_pattern_path="results/body-controller/flight-data/wing_pattern_fmech.npy"
        )
        self.wpg.reset(initial_phase=0)
        self.sensors = d.sensordata.copy()
        self.target = d.xpos[self.root].copy()
        self.heading = 0.0
        self.phase = "walking"
        self.phase_time = 0.0
        self.flight_blend = 0.0
        self.events = []
        self.takeoff_age = 0.0
        self.landed = False
        self.ground_contacts = 0
        self.command_speed = 0.0
        self.command_turn = 0.0
        self.entry_pose = d.qpos.copy()
        self.ground_action = None
        self.body_names = [
            mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b) or "world" for b in range(m.nbody)
        ]
        self.frames = []
        self.leg_actuators = []
        for a in self.views["walking"]["actions"]:
            name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, a)
            if any(part in name for part in ["T1", "T2", "T3"]) and "adhere" not in name:
                self.leg_actuators.append((a, int(m.jnt_qposadr[self.id("joint", name)])))

    def id(self, kind, name):
        found = mujoco.mj_name2id(self.model, getattr(mujoco.mjtObj, "mjOBJ_" + kind.upper()), name)
        if found < 0:
            raise ValueError(f"Missing {kind}: {name}")
        return found

    def observation(self, kind, speed, turn, height, pitch):
        d, view = self.data, self.views[kind]
        matrix = d.xmat[self.root].reshape(3, 3)
        result = {
            "walker/joints_pos": d.qpos[view["qpos"]],
            "walker/joints_vel": d.qvel[view["qvel"]],
            "walker/actuator_activation": d.act[view["act"]],
            "walker/world_zaxis": matrix[2],
        }
        for key, ids in view["sensors"].items():
            if "walker/" + key in view["info"]["observations"]:
                result["walker/" + key] = self.sensors[ids]
        if kind == "walking":
            result["walker/appendages_pos"] = (
                (d.site_xpos[view["sites"]] - d.xpos[self.root]) @ matrix
            ).reshape(-1)
        count, dt = (65, 0.002) if kind == "walking" else (6, 0.0002)
        refs = []
        rotations = []
        pos, yaw = self.target.copy(), self.heading
        inverse = d.xquat[self.root] * [1, -1, -1, -1]
        for i in range(count):
            pos[2] = height
            refs.append((pos - d.xpos[self.root]) @ matrix)
            relative = quat_mul(inverse, orientation(yaw, pitch))
            # Reference poses use the same quaternion hemisphere as the body.
            # q and -q describe one orientation; a wrapped yaw must not flip it.
            rotations.append(relative if relative[0] >= 0 else -relative)
            yaw += turn * dt
            pos[:2] += speed * dt * np.array([np.cos(yaw), np.sin(yaw)])
        result["walker/ref_displacement"] = np.asarray(refs)
        result["walker/ref_root_quat"] = np.asarray(rotations)
        return result

    def step(self, *, speed=2, turn=0, state="walking", height=2):
        d, m = self.data, self.model
        if state == "landing":
            foot_ids = self.views["walking"]["sites"][:6]
            self.ground_contacts = int(np.count_nonzero(d.site_xpos[foot_ids, 2] < 0.025))
            if d.ncon > 0 and d.xpos[self.root, 2] < 0.24 and self.ground_contacts >= 2:
                self.landed = True
            if self.landed:
                state = "walking"
        elif state == "takeoff":
            self.landed = False
        if state != self.phase:
            self.events.append(
                {
                    "time": float(d.time),
                    "from": self.phase,
                    "to": state,
                    "source": "body-controller handover",
                    "contacts": self.ground_contacts,
                }
            )
            self.phase, self.phase_time = state, 0.0
            self.entry_pose = d.qpos.copy()
            if state == "takeoff":
                self.wpg.reset(initial_phase=0)
            self.target = d.xpos[self.root].copy()
            self.heading = float(np.arctan2(d.xmat[self.root, 3], d.xmat[self.root, 0]))
        preparing = state == "takeoff" and self.phase_time < 0.3 - 1e-8
        airborne = state in ["takeoff", "flight", "landing"] and not preparing
        if preparing:
            speed, turn = 0, 0
        dt = 0.0002 if airborne else 0.002
        if not airborne:
            turn = float(np.clip(turn, -1.5, 1.5))
            if abs(turn) > 0.05 and not preparing:
                speed = max(speed, 2)
                turn = float(np.clip(turn, -speed, speed))
        self.command_speed += np.clip(speed - self.command_speed, -dt * 50, dt * 50)
        self.command_turn += np.clip(turn - self.command_turn, -dt * 10, dt * 10)
        speed, turn = self.command_speed, self.command_turn
        # The combined body retains fast wing joints even on the floor.
        # Use the published flight integration interval in every mode.
        m.opt.timestep = 0.00005
        kind = "flight" if airborne else "walking"
        self.phase_time += dt
        if state == "takeoff":
            self.takeoff_age = self.phase_time
        target_blend = 1 if airborne else 0
        self.flight_blend += np.clip(target_blend - self.flight_blend, -dt / 0.25, dt / 0.15)
        pitch = -np.deg2rad(47.5) * self.flight_blend
        goal_height = height if airborne and state != "landing" else 0.1278
        self.target[2] += np.clip(goal_height - self.target[2], -dt * 1.5, dt * 5)
        # Desired trajectories are controller inputs; actual root state is never written.
        self.heading += turn * dt
        self.target[:2] += speed * dt * np.array([np.cos(self.heading), np.sin(self.heading)])
        if airborne:
            error = self.target - d.xpos[self.root]
            length = np.linalg.norm(error)
            if length > 0.15:
                self.target = d.xpos[self.root] + error * (0.15 / length)
        hold_stance = preparing or state == "standing"
        action = (
            np.zeros(len(self.views[kind]["actions"]))
            if hold_stance
            else self.policies[kind](self.observation(kind, speed, turn, self.target[2], pitch))
        )
        if not np.isfinite(action).all():
            raise RuntimeError("Body policy returned a non-finite command")
        d.ctrl[:] = 0
        view = self.views[kind]
        if airborne:
            pattern = (
                self.wpg.get_last_angles()
                if state == "takeoff" and self.phase_time < 0.4
                else self.wpg.step(
                    ctrl_freq=self.wpg.base_beat_freq * (1 + self.wpg.rel_freq_range * action[-1])
                )
            )
            action = action.copy()
            action[3:9] += pattern - d.qpos[self.wing_q]
            d.ctrl[view["actions"]] = action[:-1]
            if state == "takeoff":
                gain = np.clip((self.phase_time - 0.4) / 0.05, 0, 1)
                rest = self.wpg.traj_ctrl[100]["traj"][0]
                preparation = 0.15 * (rest - d.qpos[self.wing_q])
                d.ctrl[self.wings] = gain * d.ctrl[self.wings] + (1 - gain) * preparation
            # Retraction uses joint targets and forces, not pose replacement.
            extension = (
                float(np.clip((0.8 - d.xpos[self.root, 2]) / 0.5, 0, 1))
                if state == "landing"
                else float(state == "takeoff")
            )
            for a, q in self.leg_actuators:
                d.ctrl[a] = (1 - extension) * m.qpos_spring[q] + extension * self.stance[q]
        else:
            d.ctrl[view["actions"]] = action
            d.ctrl[self.wings] = 0.002 * (m.qpos_spring[self.wing_q] - d.qpos[self.wing_q])
            if preparing or state == "standing":
                d.ctrl[:] = 0
                d.ctrl[self.wings] = 0.002 * (m.qpos_spring[self.wing_q] - d.qpos[self.wing_q])
                for a, q in self.leg_actuators:
                    blend = min(1, self.phase_time / 0.15)
                    d.ctrl[a] = (1 - blend) * self.entry_pose[q] + blend * self.stance[q]
                for a in self.views["walking"]["actions"][:6]:
                    d.ctrl[a] = 0
        n = round(dt / m.opt.timestep)
        sensors = np.zeros(m.nsensordata)
        for _ in range(n):
            mujoco.mj_step(m, d)
            sensors += d.sensordata
        self.sensors = sensors / n
        mujoco.mj_forward(m, d)
        if not np.isfinite(d.qpos).all() or np.max(np.abs(d.qvel)) > 1e6:
            raise RuntimeError("Body physics became unstable")
        return dt

    def snapshot(self):
        return {
            "time": float(self.data.time),
            "positions": self.data.xpos.copy(),
            "quaternions": self.data.xquat.copy(),
            "state": self.phase,
            "airborne": bool(
                self.data.xpos[self.root, 2] > 0.25
                and np.min(self.data.site_xpos[self.views["walking"]["sites"][:6], 2]) > 0.025
            ),
        }

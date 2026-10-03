"""Explicit state and arena rules added around the two frozen body policies."""

import math

from critic.body_adapter import CONFIG


def wrap_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


class BodySupervisor:
    def __init__(self):
        self.state = "standing"
        self.since = 0
        self.last_launch = -CONFIG["takeoff_refractory_seconds"]
        self.low_flight_time = 0
        self.boundary_active = False
        self.events = []
        self.pending_launch = False

    def transition(self, state, time, reason):
        if state == self.state:
            return
        self.events.append(
            {
                "time": time,
                "from": self.state,
                "to": state,
                "reason": reason,
                "source": "engineering supervisor",
            }
        )
        self.state, self.since = state, time

    def command(self, neural, *, time, dt, position, yaw, landed=False):
        if self.state in ["standing", "walking"]:
            self.transition(
                "walking"
                if self.pending_launch
                or neural["walk_speed"] > 0.05
                or abs(neural["walk_turn"]) > 0.05
                else "standing",
                time,
                "walking command",
            )
            self.pending_launch |= (
                neural["takeoff"]
                and time - self.last_launch >= CONFIG["takeoff_refractory_seconds"]
            )
            if self.pending_launch:
                self.transition("walking", time, "move inward before takeoff")
            if self.pending_launch and abs(position[0]) < 3 and abs(position[1]) < 2:
                self.transition("takeoff", time, "DNp01 threshold")
                self.last_launch = time
                self.low_flight_time = 0
                self.pending_launch = False
        elif self.state == "takeoff" and time - self.since >= 0.8 and position[2] > 0.25:
            self.transition("flight", time, "wing deployment complete and body airborne")
        elif self.state == "flight":
            if neural["flight_activity"] < CONFIG["flight_end_hz"]:
                self.low_flight_time += dt
            elif neural["flight_activity"] > CONFIG["flight_resume_hz"]:
                self.low_flight_time = 0
            if (
                time - self.since > CONFIG["minimum_flight_seconds"]
                and self.low_flight_time >= CONFIG["landing_delay_seconds"]
            ):
                self.transition("landing", time, "low DLM drive after minimum flight")
        elif self.state == "landing" and landed:
            self.transition("walking", time, "feet reached floor; walking policy resumed")
        air = self.state in ["takeoff", "flight", "landing"]
        speed = neural["flight_speed"] if air else neural["walk_speed"]
        turn = neural["flight_turn"] if air else neural["walk_turn"]
        if self.state == "takeoff":
            speed, turn = 8, 0
        elif self.state == "landing":
            speed, turn = 1, 0
        requested = {"speed": speed, "turn": turn}
        lookahead = 0.45 if air else 0.3
        predicted = [
            position[0] + speed * math.cos(yaw) * lookahead,
            position[1] + speed * math.sin(yaw) * lookahead,
        ]
        boundary = bool(
            self.pending_launch
            or (
                self.state != "takeoff"
                and (
                    abs(predicted[0]) > 7
                    or abs(predicted[1]) > 5
                    or abs(position[0]) > 8
                    or abs(position[1]) > 6
                )
            )
        )
        if boundary:
            inward = wrap_angle(math.atan2(-position[1], -position[0]) - yaw)
            limit = 5 if air else 1.5
            turn = max(-limit, min(limit, 4 * inward))
            speed = 0.75 if self.pending_launch else min(speed, 6 if air else 0.75)
        if boundary != self.boundary_active:
            self.events.append(
                {
                    "time": time,
                    "source": "arena confinement",
                    "active": boundary,
                    "requested": requested,
                    "applied": {"speed": speed, "turn": turn},
                }
            )
            self.boundary_active = boundary
        return {
            "state": self.state,
            "speed": speed,
            "turn": turn,
            "height": CONFIG["flight_height_cm"],
            "boundary": boundary,
            "requested": requested,
        }

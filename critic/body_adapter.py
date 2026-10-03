"""A declared engineering conversion from annotated spikes to body commands.

All inputs are absolute spikes/s/cell. No text, audio, sampled display neurons,
silence subtraction, or reader identity enters this adapter.
"""

import math

GROUPS = {
    "motor_walk": [("DNg100", None)],
    "motor_turn_left": [("DNa02", "L")],
    "motor_turn_right": [("DNa02", "R")],
    "motor_takeoff": [("DNp01", None)],
    "motor_flight": [("DLMn a, b", None), ("DLMn c-f", None)],
    "motor_flight_left": [("b1 MN", "L"), ("b2 MN", "L")],
    "motor_flight_right": [("b1 MN", "R"), ("b2 MN", "R")],
}

CONFIG = {
    "version": "neural-body-adapter-v1",
    "dt": 0.02,
    "smoothing_seconds": 0.2,
    "walking_gain_cm_s_per_hz": 0.4,
    "maximum_walking_cm_s": 4,
    "walking_turn_gain_rad_s_per_hz": 0.3,
    "maximum_walking_turn_rad_s": 3,
    "takeoff_threshold_hz": 2,
    "takeoff_rearm_hz": 0.5,
    "flight_base_cm_s": 6,
    "flight_gain_cm_s_per_hz": 2,
    "maximum_flight_cm_s": 20,
    "flight_turn_gain_rad_s_per_hz": 0.15,
    "maximum_flight_turn_rad_s": 3,
    "flight_end_hz": 0.35,
    "flight_resume_hz": 0.75,
    "minimum_flight_seconds": 1,
    "landing_delay_seconds": 0.4,
    "takeoff_refractory_seconds": 4,
    "flight_height_cm": 2,
}


def population_indices(metadata):
    import numpy as np

    result = {}
    for name, selectors in GROUPS.items():
        mask = np.zeros(len(metadata["cell_type"]), dtype=bool)
        for cell_type, side in selectors:
            selected = metadata["cell_type"] == cell_type
            if side:
                selected &= metadata["side"] == side
            mask |= selected
        result[name] = np.flatnonzero(mask)
        if not len(result[name]):
            raise ValueError(f"Missing annotated motor population: {name}")
    return result


class NeuralBodyAdapter:
    def __init__(self, config=None):
        self.config = dict(config or CONFIG)
        self.rates = {k: 0.0 for k in GROUPS}
        self.armed = True

    def step(self, rates):
        c = self.config
        alpha = -math.expm1(-c["dt"] / c["smoothing_seconds"])
        for key in self.rates:
            rate = rates[key]
            if not math.isfinite(rate) or rate < 0:
                raise ValueError(f"Invalid firing rate: {key}")
            self.rates[key] += alpha * (rate - self.rates[key])
        r = self.rates
        launch = bool(self.armed and r["motor_takeoff"] >= c["takeoff_threshold_hz"])
        if launch:
            self.armed = False
        elif r["motor_takeoff"] < c["takeoff_rearm_hz"]:
            self.armed = True
        return {
            "walk_speed": min(
                c["maximum_walking_cm_s"], c["walking_gain_cm_s_per_hz"] * r["motor_walk"]
            ),
            "walk_turn": max(
                -c["maximum_walking_turn_rad_s"],
                min(
                    c["maximum_walking_turn_rad_s"],
                    c["walking_turn_gain_rad_s_per_hz"]
                    * (r["motor_turn_left"] - r["motor_turn_right"]),
                ),
            ),
            "takeoff": launch,
            "flight_speed": min(
                c["maximum_flight_cm_s"],
                c["flight_base_cm_s"] + c["flight_gain_cm_s_per_hz"] * r["motor_flight"],
            ),
            "flight_turn": max(
                -c["maximum_flight_turn_rad_s"],
                min(
                    c["maximum_flight_turn_rad_s"],
                    c["flight_turn_gain_rad_s_per_hz"]
                    * (r["motor_flight_left"] - r["motor_flight_right"]),
                ),
            ),
            "flight_activity": r["motor_flight"],
        }

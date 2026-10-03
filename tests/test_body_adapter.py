import math

import numpy as np
import pytest

from critic.body_adapter import CONFIG, GROUPS, NeuralBodyAdapter, population_indices
from critic.body_supervisor import BodySupervisor


def rates(**changes):
    return {**dict.fromkeys(GROUPS, 0.0), **changes}


def response(**changes):
    adapter = NeuralBodyAdapter()
    for _ in range(100):
        command = adapter.step(rates(**changes))
    return command


def test_each_motor_signal_controls_only_its_declared_command():
    base = response()
    for signal, field, direction in [
        ("motor_walk", "walk_speed", 1),
        ("motor_turn_left", "walk_turn", 1),
        ("motor_turn_right", "walk_turn", -1),
        ("motor_flight_left", "flight_turn", 1),
        ("motor_flight_right", "flight_turn", -1),
    ]:
        actual = response(**{signal: 2})
        assert direction * (actual[field] - base[field]) > 0
        assert {k: v for k, v in actual.items() if k != field} == {
            k: v for k, v in base.items() if k != field
        }
    flight = response(motor_flight=2)
    assert flight["flight_speed"] > base["flight_speed"]
    assert not flight["takeoff"]
    assert response(motor_walk=1e6)["walk_speed"] == CONFIG["maximum_walking_cm_s"]


def test_takeoff_requires_a_crossing_and_rearms_after_quiet():
    adapter = NeuralBodyAdapter()
    assert adapter.step(rates(motor_takeoff=25))["takeoff"]
    assert not adapter.step(rates(motor_takeoff=25))["takeoff"]
    for _ in range(100):
        assert not adapter.step(rates())["takeoff"]
    assert adapter.step(rates(motor_takeoff=25))["takeoff"]


def test_identical_and_clamped_inputs_remove_sound_dependent_commands():
    a, b, clamped = NeuralBodyAdapter(), NeuralBodyAdapter(), NeuralBodyAdapter()
    varied = []
    null = []
    for i in range(200):
        row = rates(motor_walk=3 if i % 20 < 10 else 0)
        assert a.step(row) == b.step(row)
        varied.append(b.rates["motor_walk"])
        null.append(clamped.step(rates())["walk_speed"])
    assert max(varied) > 1
    assert null == [0] * 200


@pytest.mark.parametrize("bad", [-1, math.nan, math.inf])
def test_invalid_activity_fails_without_a_silent_substitution(bad):
    with pytest.raises(ValueError, match="Invalid firing rate"):
        NeuralBodyAdapter().step(rates(motor_walk=bad))


def test_annotation_capture_uses_all_matching_cells_and_requires_each_group():
    cell_types, sides = [], []
    for selectors in GROUPS.values():
        for name, side in selectors:
            cell_types.extend([name] * 2)
            sides.extend([side or "L"] * 2)
    data = {"cell_type": np.array(cell_types), "side": np.array(sides)}
    groups = population_indices(data)
    assert len(groups["motor_walk"]) == 2
    assert len(groups["motor_flight"]) == 4
    assert not set(groups["motor_turn_left"]) & set(groups["motor_turn_right"])
    data["cell_type"][groups["motor_walk"]] = "unknown"
    with pytest.raises(ValueError, match="motor_walk"):
        population_indices(data)


def test_supervisor_waits_for_contact_and_records_arena_interventions():
    supervisor = BodySupervisor()
    command = response()
    command["takeoff"] = True

    def step(time, position=(0, 0, 2), landed=False):
        return supervisor.command(
            command, time=time, dt=0.02, position=position, yaw=0, landed=landed
        )

    assert step(0)["state"] == "takeoff"
    command["takeoff"] = False
    assert step(1)["state"] == "flight"
    for i in range(110, 230):
        current = step(i / 100)
    assert current["state"] == "landing"
    assert step(3, (0, 0, 0.13))["state"] == "landing"
    assert step(3.1, (0, 0, 0.13), True)["state"] == "walking"
    command["walk_speed"] = 2
    constrained = step(4, (8, 0, 0.13))
    assert constrained["boundary"]
    assert constrained["requested"] != {k: constrained[k] for k in ["speed", "turn"]}
    assert supervisor.events[-1]["source"] == "arena confinement"

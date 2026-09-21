import json
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from critic.passages import bins, smooth_drive
from critic.population_reading import ReadingInput, interpret
from critic.population_screen import bounds, evidence, select_candidates, survives

ROOT = Path(__file__).resolve().parents[1]


def test_complete_native_bins_and_amplitude_control():
    assert bounds([0.11, 0.59], 100) == (2, 5)
    windows = {"reference": [0.3, 1.5], "human": [0.3, 1.5]}
    reference = np.ones((8, 30))
    human = 2 * reference
    predictions = {"0": {"reference": np.ones(30), "human": 2 * np.ones(30)}}
    result = evidence(reference, human, windows, predictions)
    assert result["raw"][4]["criterion_met"]
    assert not result["qualifies"]
    assert result["residuals"]["0"][4]["zero"] == 8


def test_direction_must_survive_and_selection_stays_discovery_only():
    assert not survives({"direction": 1}, {"direction": -1, "qualifies": True})
    assert not survives({"direction": 1}, {"direction": 1, "qualifies": False})
    rows = [
        {"type": str(i), "stanza": 1, "evidence": {"qualifies": i > 0, "strength": i}}
        for i in range(8)
    ]
    assert [r["type"] for r in select_candidates(rows)] == ["7", "6", "5", "4", "3"]


def test_candidates_reconstruct_from_saved_counts():
    folder = ROOT / "experiments/populations-v6"
    discovery = json.loads((folder / "discovery.json").read_text())
    result = json.loads((folder / "comparison.json").read_text())
    selected = select_candidates(discovery["screen"])
    assert [(r["type"], r["stanza"]) for r in selected] == [
        (r["type"], r["stanza"]) for r in result["candidates"]
    ]
    manifest = json.loads((ROOT / "experiments/delivery-v1/manifest.json").read_text())
    drive = {
        n: np.array(
            [
                f["injected_voltage"]
                for f in json.loads(
                    (ROOT / f"experiments/delivery-v1/{n}/encoding.json").read_text()
                )
            ]
        )
        for n in ["reference", "human"]
    }
    with np.load(folder / "validation-counts.npz") as p:
        for row in result["candidates"]:
            j = next(i for i, e in enumerate(discovery["eligible"]) if e["type"] == row["type"])
            rates = {
                n: (p[n][:, 0, :, j].astype(float) - p[n][:, 1, :, j]) / (0.1 * row["total"])
                for n in drive
            }
            first = [1, 6, 11, 16, 21][row["stanza"] - 1]
            windows = {}
            for n in drive:
                lines = {v["line"]: v for v in manifest["conditions"][n]["lines"]}
                windows[n] = [lines[first]["start"], lines[first + 3]["end"]]
            predictions = {
                k: {n: bins(g * smooth_drive(x, float(k))) for n, x in drive.items()}
                for k, g in row["gains"].items()
            }
            actual = evidence(rates["reference"], rates["human"], windows, predictions)
            assert actual["raw"][4]["mean"] == pytest.approx(
                row["validation"]["raw"][4]["mean"], abs=1e-12
            )
            assert survives(row["discovery"], actual) == row["survives"]
            for k in predictions:
                assert actual["residuals"][k][4]["mean"] == pytest.approx(
                    row["validation"]["residuals"][k][4]["mean"], abs=1e-12
                )


def test_reading_boundary_and_null():
    assert "does not establish" in interpret(ReadingInput(candidates=[]))
    with pytest.raises(ValidationError):
        ReadingInput(candidates=[], poem="Little fly")

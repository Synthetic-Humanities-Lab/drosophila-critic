import json
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from critic.passage_reading import ReadingInput, interpret
from critic.passages import bins, compare_passage, fit_gain, score, smooth_drive

ROOT = Path(__file__).resolve().parents[1]


def test_external_baseline_recovers_gain_without_looking_ahead():
    drive = np.arange(100) / 100
    response = np.tile(3 * drive, (8, 1))
    assert fit_gain(drive, response, 0) == pytest.approx(3)
    assert score(response, 3 * drive)["r2"] == pytest.approx(1)
    later = drive.copy()
    later[50:] = 100
    np.testing.assert_array_equal(smooth_drive(drive, 0.1)[:50], smooth_drive(later, 0.1)[:50])
    assert np.all(smooth_drive(np.zeros(100), 0.3) == 0)


def test_passages_keep_native_durations_and_nulls():
    reference = np.ones((8, 100))
    human = np.ones((8, 200))
    c = compare_passage(reference, human, [0, 1], [1, 3])
    assert c["mean"] == 0
    assert not c["boundary_robust"]
    assert c["zero"] == 8
    c = compare_passage(reference, human * 2, [0, 1], [1, 3])
    assert c["mean"] == 1
    assert c["boundary_robust"]


def test_saved_passage_four_reconstructs_from_integer_counts():
    result = json.loads((ROOT / "experiments/passages-v5/comparison.json").read_text())
    manifest = result["conditions"]
    inventory = json.loads((ROOT / "docs/population-inventory.json").read_text())
    group = "direct JON postsynaptic partners"
    size = inventory["groups"][group]["count"]
    rates = {}
    with np.load(ROOT / "experiments/temporal-v2/counts.npz") as p:
        j = list(p["group_names"]).index(group)
        for name in ["reference", "human"]:
            n = manifest[name]["frames"]
            rates[name] = np.array(
                [
                    (
                        p[f"{name}_{s}_group_counts"][75 : 75 + n, j].astype(np.int64)
                        - p[f"silence_{n}_{s}_group_counts"][75 : 75 + n, j].astype(np.int64)
                    )
                    / (0.02 * size)
                    for s in result["seeds"]
                ]
            )
    passage = result["passages"][3]
    windows = []
    for name in ["reference", "human"]:
        lines = {line["line"]: line for line in manifest[name]["lines"]}
        windows.append([lines[16]["start"], lines[19]["end"]])
    actual = compare_passage(rates["reference"], rates["human"], *windows)
    saved = passage["comparisons"][group]
    assert actual["mean"] == pytest.approx(saved["mean"], abs=1e-12)
    assert actual["boundary_robust"] == saved["boundary_robust"]
    for key, model in result["models"].items():
        drive = np.array(
            [
                f["injected_voltage"]
                for f in json.loads(
                    (ROOT / "experiments/temporal-v2/human-encoding.json").read_text()
                )
            ]
        )
        prediction = model["gain"] * smooth_drive(drive, model["tau"])
        np.testing.assert_allclose(
            bins(prediction), result["timeline"]["human"]["predictions"][key], atol=1e-12
        )
        assert score(rates["human"], prediction)["r2"] == pytest.approx(
            model["scores"]["human"]["r2"], abs=1e-12
        )


def test_interpreter_accepts_only_response_and_retains_limit():
    data = json.loads((ROOT / "experiments/passages-v5/interpretation-input.json").read_text())
    validated = ReadingInput(**data)
    assert interpret(validated)["text"]
    with pytest.raises(ValidationError):
        ReadingInput(**data, poem="Little fly")
    data["passages"][0]["text"] = "Little fly"
    with pytest.raises(ValidationError):
        ReadingInput(**data)

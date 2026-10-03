"""Audit the shipped trajectories at the data-to-renderer boundary."""

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
EDITION = ROOT / "experiments/encounter-v3"
MANIFEST = json.loads((EDITION / "manifest.json").read_text())


@pytest.mark.parametrize(
    "entry", MANIFEST["body"]["runs"], ids=lambda r: f"{r['reader']}-{r['condition']}-{r['seed']}"
)
def test_saved_poses_are_complete_bounded_and_match_their_manifest(entry):
    raw = (EDITION / entry["path"]).read_bytes()
    assert len(raw) == entry["bytes"]
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    record = json.loads(gzip.decompress(raw))
    assert record["metrics"]["complete"] and not record["metrics"]["failures"]
    assert record["provenance"]["seed"] == entry["seed"]
    assert record["provenance"]["condition"] == entry["condition"]
    times = np.array(record["time"])
    positions = np.array(record["positions"])
    rotations = np.array(record["quaternions"])
    assert np.isfinite(positions).all() and np.isfinite(rotations).all()
    assert positions.shape == (len(times), len(record["body_names"]), 3)
    assert rotations.shape == (*positions.shape[:2], 4)
    assert len(record["commands"]) == len(record["airborne"]) == len(record["states"]) == len(times)
    assert np.allclose(np.linalg.norm(rotations, axis=2), 1, atol=2e-6)
    assert np.all(np.diff(times) > 0)
    assert np.max(np.abs(np.diff(times) - 0.02)) < 0.0021
    root = positions[:, record["body_names"].index("walker/thorax")]
    assert np.max(np.abs(root[:, 0])) < 10
    assert np.max(np.abs(root[:, 1])) < 8
    assert 0 <= root[:, 2].min() <= root[:, 2].max() < 10
    assert all(isinstance(c["boundary"], bool) for c in record["commands"])
    assert all("body_reference_speed" in c for c in record["commands"])
    assert sum(record["airborne"]) * 0.02 == pytest.approx(record["metrics"]["flight_seconds"])


def test_aggregate_measurements_use_all_four_paired_runs_and_one_display_seed():
    summary = json.loads((EDITION / "movement-summary.json").read_text())
    assert MANIFEST["body"]["qualified"]
    assert len(MANIFEST["body"]["runs"]) == 16
    assert summary["seed"] == MANIFEST["body"]["seed"] == 1101
    for reader, r in summary["performances"].items():
        assert r["paired_seeds"] == [1101, 1102, 1103, 1104]
        for condition in ["sound", "silence"]:
            assert (
                MANIFEST["performances"][reader][f"{condition}_body"]
                == f"{reader}-{condition}-1101.json.gz"
            )
        for metric, stats in r["summary"].items():
            a = {x["seed"]: x["metrics"][metric] for x in r["runs"]["sound"]}
            b = {x["seed"]: x["metrics"][metric] for x in r["runs"]["silence"]}
            changes = [a[s] - b[s] for s in r["paired_seeds"]]
            assert stats["change"]["mean"] == pytest.approx(np.mean(changes))
            assert stats["change"]["minimum"] == min(changes)
            assert stats["change"]["maximum"] == max(changes)

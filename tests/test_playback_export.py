import json
from pathlib import Path

import numpy as np

from scripts.export_encounter_playback import aggregate, spatial_silence

ROOT = Path(__file__).resolve().parents[1]


def test_last_partial_bin_uses_its_actual_duration():
    result = aggregate(np.ones((7, 2)), np.array([1, 2]))
    assert np.array_equal(result, [[50, 25], [50, 25]])


def test_spatial_silence_uses_silence_spikes_at_the_same_neuron_coordinates(tmp_path):
    template = dict(neuron_indices=[2, 5], displayed_neurons=2, firing_bins=[[0]])
    path = tmp_path / "spikes.npz"
    np.savez(path, neuron_indices=[1, 5, 5], offsets=[0, 1, 1, 2, 2, 2, 3])
    actual = spatial_silence(template, path)
    assert actual["firing_bins"] == [[1], [1]]
    assert actual["neuron_indices"] == template["neuron_indices"]
    assert template["firing_bins"] == [[0]]


def test_published_playback_matches_the_historical_measurements():
    previous = json.loads((ROOT / "experiments/encounter-v1/result.json").read_text())
    manifest = json.loads((ROOT / "experiments/encounter-v2/manifest.json").read_text())
    for key in ("a", "b"):
        record = json.loads((ROOT / f"experiments/encounter-v2/playback-{key}.json").read_text())
        assert record["playback_duration"] > record["audio_duration"] + 3
        assert record["seeds"] == previous["seeds"]
        old = previous["response"]["performances"][key]["populations"]
        assert np.isclose(record["summary"][2]["sound"]["mean"], old[1]["raw_rate"]["mean"])
        assert np.isclose(record["summary"][2]["change"]["mean"], old[1]["rate"]["mean"])
        mean = np.asarray(record["activity"]["sound"]["mean"])
        silence = np.asarray(record["activity"]["silence"]["mean"])
        assert np.allclose(mean - silence, record["activity"]["change"]["mean"])
        assert len(record["summary"]) == len(manifest["groups"])
        for field, scale in manifest["input_scales"].items():
            assert max(record["input"][field]) <= scale

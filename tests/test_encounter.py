from types import SimpleNamespace

import numpy as np

from scripts.build_encounter import load_record


def test_mechanical_decay_is_persistence_and_type_counts_follow_corrected_phases(tmp_path):
    phase = np.array(["warmup", "baseline", "audio", "audio", "audio", "tail"])
    np.savez(tmp_path / "populations.npz", phase=phase, group_names=["g"], type_names=["a", "b"])
    np.savez(tmp_path / "spikes.npz", neuron_indices=[0, 1, 0, 1, 1, 0], offsets=np.arange(7))
    runner = SimpleNamespace(
        groups={"g": [0, 1]}, type_names=["a", "b"], type_index=np.array([0, 1])
    )
    r = load_record(tmp_path, runner, sound_frames=2)
    assert r["phase"].tolist() == ["warmup", "baseline", "audio", "audio", "tail", "tail"]
    assert r["phase_type_counts"].tolist() == [[0, 1], [1, 1], [1, 1]]


def test_public_reading_uses_numeric_summary_and_preserves_null():
    from critic.encounter_reading import interpret
    from critic.performance_reading import ComparisonSummary

    summary = ComparisonSummary(
        durations=[1, 1],
        seeds=[1, 2],
        differences=[
            dict(
                population="direct JON postsynaptic partners",
                mean_rate_difference=0,
                seed_differences=[0, 0],
                persistence_difference=0,
                temporal_separation_rms=0,
                temporal_variability_rms=0,
            )
        ],
    )
    assert "no basis" in interpret(summary)
    summary.differences[0].temporal_separation_rms = 1
    assert "different moments" in interpret(summary)

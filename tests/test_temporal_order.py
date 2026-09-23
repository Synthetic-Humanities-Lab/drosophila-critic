import numpy as np
import pytest

from scripts.temporal_order import stimuli, temporal_summary


def test_permutations_preserve_values_and_invert_with_remainder():
    x = np.arange(53) / 100
    waves, orders = stimuli(x)
    for name, order in orders.items():
        np.testing.assert_array_equal(np.sort(waves[name]), x)
        np.testing.assert_array_equal(waves[name][np.argsort(order)], x)
        np.testing.assert_array_equal(waves[name][-3:], x[-3:])
        assert waves[name].mean() == pytest.approx(x.mean())
    assert not np.array_equal(waves["reverse"], x)
    assert not np.array_equal(waves["shuffle"], x)
    assert waves["constant"].sum() == pytest.approx(x.sum())
    assert not waves["silence"].any()


def test_temporal_diagnostic_distinguishes_repeating_from_cancelled_effect():
    common = np.arange(30).reshape(10, 3)
    same = temporal_summary(np.array([common] * 4))
    assert same["leave_one_seed_out_cosine"][0] == pytest.approx([1, 1, 1])
    assert same["descriptive_ratio"] == [None] * 3
    cancel = temporal_summary(np.array([common, -common, common, -common]))
    assert cancel["rms_mean_difference"] == [0] * 3
    assert cancel["leave_one_seed_out_cosine"][0] == pytest.approx([-1, -1, -1])


@pytest.mark.parametrize("x", [[], [np.nan] * 10, [-0.1] * 10, [0.9] * 10])
def test_invalid_input(x):
    with pytest.raises(ValueError):
        stimuli(x)

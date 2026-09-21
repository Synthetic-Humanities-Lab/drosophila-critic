import numpy as np
import pytest

from critic.receiver import require_validated_receiver
from critic.receiver.acoustics import (
    ReceiverConfig,
    particle_velocity,
    prepare_waveform,
    project_axes,
)
from critic.receiver.adaptation import Adaptation, AdaptationConfig
from critic.receiver.mechanics import SourceOscillator
from critic.receiver.timing import DelayedFlyBrain, SimulationConfig


def test_reference_calibration_and_direction():
    t = np.arange(48000) / 48000
    tone = np.sqrt(2) * 0.1 * np.sin(2 * np.pi * 200 * t)
    field = particle_velocity(tone)
    assert np.sqrt(np.mean(field[:, 0] ** 2)) == pytest.approx(0.5)
    assert np.all(field[:, 1] == 0)
    left = project_axes(particle_velocity(tone, ReceiverConfig(azimuth_degrees=30)), [-45, 45])
    right = project_axes(particle_velocity(tone, ReceiverConfig(azimuth_degrees=-30)), [-45, 45])
    np.testing.assert_allclose(left, right[:, ::-1], atol=1e-15)


def test_resampling_preserves_level_without_normalizing():
    x = 0.01 * np.sin(2 * np.pi * 200 * np.arange(24000) / 24000)
    y, info = prepare_waveform(x, 24000)
    assert len(y) == 48000
    assert info["linear_gain"] == 1
    assert np.sqrt(np.mean(y**2)) == pytest.approx(np.sqrt(np.mean(x**2)), rel=0.002)
    assert not np.any(prepare_waveform(np.zeros(240), 24000)[0])
    for bad in [[], [np.nan], [[1, 2, 3]]]:
        with pytest.raises(ValueError):
            prepare_waveform(bad, 24000)


def test_oscillator_chunk_reset_and_convergence():
    model = SourceOscillator()
    full = model.advance(4800)
    model.reset()
    chunks = np.concatenate([model.advance(100), model.advance(4700)])
    np.testing.assert_array_equal(full, chunks)
    fine = SourceOscillator(1 / 96000).advance(9600)[::2]
    for column in [0, 1]:
        assert (
            np.linalg.norm(full[:, column] - fine[:, column]) / np.linalg.norm(fine[:, column])
            < 0.02
        )
    # This source model oscillates without sound; do not pass it off as a healthy baseline.
    assert np.max(np.abs(full[:, 1])) > 0.01


def test_adaptation_chunk_reset_and_offset_rejection():
    x = np.ones(48000)
    a = Adaptation()
    full = a.process(x)
    assert full[-1] < full[0] * 1e-8
    a.reset()
    np.testing.assert_array_equal(full, np.r_[a.process(x[:137]), a.process(x[137:])])
    a.reset()
    assert not np.any(a.process(np.zeros(10)))
    with pytest.raises(ValueError):
        AdaptationConfig(sigma_div=float("nan"))


def test_production_gate_fails_closed():
    with pytest.raises(RuntimeError, match="current calibration"):
        require_validated_receiver()


class TinyBrain:
    """Impulse fixture tests delay semantics without a 166k-neuron download."""

    device, batch, refractory_steps, n, tau = "cpu", 1, 0, 2, 0.1

    def __init__(self, dt):
        self.dt = dt

    def reset(self, seed):
        self.fired = np.array([], dtype=np.int64)
        self.steps = 0
        self.delivered = []

    def step(self, inject):
        self.delivered.append(self.fired.copy())
        self.steps += 1
        return np.array([0], dtype=np.int64) if self.steps == 1 else np.array([], dtype=np.int64)


@pytest.mark.parametrize("dt", [0.020, 0.0005, 0.00025])
def test_explicit_delay(dt):
    b = TinyBrain(dt)
    a = DelayedFlyBrain(b, SimulationConfig(dt_seconds=dt))
    for _ in range(a.delay_steps + 1):
        a.step()
    assert not any(len(x) for x in b.delivered[: a.delay_steps])
    np.testing.assert_array_equal(b.delivered[a.delay_steps], [0])
    a.reset()
    assert not any(len(x) for x in a.pending)


def test_adaptation_agrees_with_independent_linear_filter():
    from scipy.signal import lfilter

    x = np.random.default_rng(2).normal(size=4096) * 1e5
    c = AdaptationConfig()
    a = np.exp(-c.dt_seconds / c.tau_sub_seconds)
    b = np.exp(-c.dt_seconds / c.tau_div_seconds)
    rectified = abs(x - lfilter([1 - a], [1, -a], x))
    expected = rectified / (1 / c.sigma_div + lfilter([1 - b], [1, -b], rectified))
    np.testing.assert_allclose(Adaptation(c).process(x), expected, rtol=1e-12)


def test_invalid_config_and_state_unchanged_after_invalid_audio():
    with pytest.raises(ValueError):
        ReceiverConfig(reference_digital_rms=0)
    with pytest.raises(ValueError):
        SimulationConfig(dt_seconds=0.001)
    a = Adaptation()
    a.process([1.0])
    before = (a.mean, a.level)
    with pytest.raises(ValueError):
        a.process([np.nan])
    assert before == (a.mean, a.level)


def test_current_integration_and_validation():
    class CaptureBrain(TinyBrain):
        def step(self, inject):
            self.injections = inject
            return np.array([], dtype=np.int64)

    b = CaptureBrain(0.0005)
    a = DelayedFlyBrain(b)
    a.step([(np.array([0]), 20)])
    assert b.injections[0][1] == pytest.approx(20 * 0.1 * (1 - np.exp(-0.0005 / 0.1)))
    with pytest.raises(ValueError):
        a.step([(np.array([-1]), 20)])
    with pytest.raises(ValueError):
        a.step([(np.array([0]), float("inf"))])

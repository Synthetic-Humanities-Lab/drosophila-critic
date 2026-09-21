import numpy as np
import pytest
from scipy.integrate import solve_ivp

from critic.receiver.healthy import (
    SOURCE_FITS,
    ForceTransducer,
    SoundTransfer,
    SoundTransferConfig,
    _rhs,
)


def phasor(values, frequency, rate):
    t = np.arange(len(values)) / rate
    return 2 * np.mean(values * np.exp(-2j * np.pi * frequency * t))


@pytest.mark.parametrize("frequency", [100, 200, 394, 600, 1500])
def test_sound_transfer_matches_published_fit_function(frequency):
    rate = 48000
    t = np.arange(rate) / rate
    air = np.cos(2 * np.pi * frequency * t)
    model = SoundTransfer()
    velocity = model.process(air)[:, 1] / 1e6
    observed = phasor(velocity[rate // 2 :], frequency, rate) / phasor(
        air[rate // 2 :], frequency, rate
    )
    # The interval-held drive introduces its known half-sample lag and sinc gain.
    hold = np.sinc(frequency / rate) * np.exp(-1j * np.pi * frequency / rate)
    assert observed == pytest.approx(model.velocity_transfer(frequency) * hold, rel=0.005)
    assert SoundTransfer().velocity_transfer(394) == pytest.approx(1.13)


def test_sound_state_chunks_and_silence():
    x = np.random.default_rng(4).normal(size=1000)
    model = SoundTransfer()
    full = model.process(x)
    model.reset()
    np.testing.assert_array_equal(
        full, np.concatenate([model.process(x[:11]), model.process(x[11:])])
    )
    model.reset()
    assert not np.any(model.process(np.zeros(50)))
    with pytest.raises(ValueError):
        SoundTransferConfig(quality_factor=-1)


@pytest.mark.parametrize("parameters", SOURCE_FITS)
def test_force_fixed_point_step_and_independent_integrator(parameters):
    model = ForceTransducer(parameters)
    trace = model.process(np.zeros(20))
    np.testing.assert_allclose(trace[:, :4], 0, atol=1e-12)
    np.testing.assert_allclose(trace[:, 4:6], parameters.resting_open_probability)
    assert np.max(np.abs(trace[:, 6])) < 1e-15
    model.reset()
    n = 480
    trace = model.process(np.full(n, 2.0))
    reference = solve_ivp(
        lambda _, y: _rhs(y, 2.0, model.p),
        (0, 10),
        np.zeros(4),
        method="DOP853",
        rtol=1e-10,
        atol=1e-10,
        t_eval=np.arange(n) / 48,
    )
    np.testing.assert_allclose(trace[:, :4], reference.y.T, atol=1e-3, rtol=1e-4)
    assert np.all((trace[:, 4:6] >= 0) & (trace[:, 4:6] <= 1))


def test_force_symmetry_chunking_and_convergence():
    x = np.sin(np.arange(4800) / 48000 * 2 * np.pi * 200) * 3
    model = ForceTransducer(SOURCE_FITS[6])
    full = model.process(x)
    model.reset()
    np.testing.assert_array_equal(
        full, np.concatenate([model.process(x[:71]), model.process(x[71:])])
    )
    reversed_force = ForceTransducer(SOURCE_FITS[6]).process(-x)
    np.testing.assert_allclose(full[:, 0], -reversed_force[:, 0], atol=1e-10)
    np.testing.assert_allclose(full[:, 4], reversed_force[:, 5], atol=1e-10)
    fine = ForceTransducer(SOURCE_FITS[6], dt_seconds=1 / 96000).process(np.repeat(x, 2))[::2]
    np.testing.assert_allclose(full, fine, rtol=1e-3, atol=1e-3)


def test_analytic_jacobian_matches_finite_difference():
    for parameters in SOURCE_FITS:
        model = ForceTransducer(parameters)
        epsilon = 1e-4
        numeric = np.column_stack(
            [
                (
                    _rhs(np.eye(4)[i] * epsilon, 0, model.p)
                    - _rhs(-np.eye(4)[i] * epsilon, 0, model.p)
                )
                / (2 * epsilon)
                for i in range(4)
            ]
        )
        np.testing.assert_allclose(numeric, model.jacobian(), atol=1e-7)


def test_saved_calibration_preserves_limits_and_source_discrepancies():
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "experiments/receiver-v2/calibration.json"
    report = json.loads(path.read_text())
    assert report["production_receiver_changed"] is False
    assert all(
        row["neural_response"] is None and row["reading"] is None
        for row in report["recordings"].values()
    )
    audit = report["parameter_audit"]
    assert [
        row["parameters"]["fly"] for row in audit["fits"] if not row["motor_time_within_5_percent"]
    ] == [1, 6]
    assert all(row["applied"] is False for row in audit["unapplied_transposition_hypothesis"])
    assert report["diagnostics"]["numerical_convergence_pass_2_percent"]
    for row in report["diagnostics"]["force_transduction_tones"]:
        if row["force_peak_pn"] == 0.01:
            assert row["displacement_fundamental_gain_nm_pn"] == pytest.approx(
                row["small_signal_gain_nm_pn"], rel=0.005
            )


def test_physical_inputs_reject_nonfinite_without_corrupting_state():
    for model in [SoundTransfer(), ForceTransducer(SOURCE_FITS[6])]:
        before = model.state.copy()
        with pytest.raises(ValueError):
            model.process([np.nan])
        np.testing.assert_array_equal(before, model.state)


@pytest.mark.parametrize("index", [1, 2, 3, 4, 6])
def test_consistent_source_time_constants_have_correct_physical_units(index):
    p = SOURCE_FITS[index]
    derived = ForceTransducer(p).derived_constants()
    assert derived["tau_motor_ms"] == pytest.approx(p.published_tau_motor_ms, rel=0.05)
    assert derived["tau_receiver_ms"] == pytest.approx(p.published_tau_receiver_ms, rel=0.05)
    assert derived["thermal_energy_pn_nm_from_eq2"] == pytest.approx(4.0, rel=0.02)

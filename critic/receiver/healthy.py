"""Published sound-transfer reference and force-driven transduction model.

These are separate source models, not a calibrated end-to-end neural receiver.
Nadrowski et al. 2008 SI eqs 1-6 are expressed about their zero-force fixed point.
Units internally: nanometres, milliseconds, piconewtons.
"""

from dataclasses import asdict, dataclass

import numpy as np
from numba import njit
from scipy.linalg import expm


@dataclass(frozen=True)
class SoundTransferConfig:
    """Gopfert & Robert 2002 Fig. 2C, one representative fitted response."""

    resonance_hz: float = 394.0
    quality_factor: float = 1.24
    velocity_gain_at_resonance: float = 1.13
    dt_seconds: float = 1 / 48000

    def __post_init__(self):
        if not all(np.isfinite(v) and v > 0 for v in asdict(self).values()):
            raise ValueError("Sound-transfer parameters must be finite and positive")
        if self.dt_seconds > 1 / 48000:
            raise ValueError("Receiver sampling must be at least 48 kHz")


@njit
def _linear_step(values, state, transition, forcing):
    output = np.empty((len(values), 2))
    for i in range(len(values)):
        output[i] = state
        state = transition @ state + forcing * values[i]
    return output, state


class SoundTransfer:
    """Measured-fit linear reference, with no separate active amplifier added.

    x'' + omega/Q x' + omega**2 x = gain*omega/Q * air_velocity.
    Its velocity transfer has the published resonant gain and phase convention.
    Exact zero-order-hold state transition; outputs are interval-start states.
    """

    def __init__(self, config=SoundTransferConfig()):
        self.config = config
        omega = 2 * np.pi * config.resonance_hz
        damping = omega / config.quality_factor
        augmented = np.array(
            [
                [0, 1, 0],
                [-(omega**2), -damping, config.velocity_gain_at_resonance * damping],
                [0, 0, 0],
            ],
            dtype=float,
        )
        transition = expm(augmented * config.dt_seconds)
        self.transition, self.forcing = transition[:2, :2].copy(), transition[:2, 2].copy()
        self.reset()

    def reset(self):
        self.state = np.zeros(2)

    def process(self, air_velocity_mm_s):
        x = _finite_vector(air_velocity_mm_s)
        # mm/s -> nm/s; returned columns nm and nm/s.
        out, state = _linear_step(x * 1e6, self.state, self.transition, self.forcing)
        if not np.all(np.isfinite(out)) or not np.all(np.isfinite(state)):
            raise FloatingPointError("Sound transfer overflow; state not committed")
        self.state = state
        return out

    def velocity_transfer(self, frequency_hz):
        c = self.config
        s = 2j * np.pi * np.asarray(frequency_hz)
        omega = 2 * np.pi * c.resonance_hz
        return (
            c.velocity_gain_at_resonance
            * omega
            / c.quality_factor
            * s
            / (s**2 + omega / c.quality_factor * s + omega**2)
        )


@dataclass(frozen=True)
class TransducerParameters:
    fly: int
    k_gs_pn_nm: float
    k_joint_pn_nm: float
    feedback_s: float
    resting_open_probability: float
    delta_nm: float
    channels_per_population: int
    friction_1e9_kg_s: float
    motor_friction_1e9_kg_s: float
    mass_1e12_kg: float
    gating_swing_nm: float
    stall_force_pn: float
    feedback_force_pn: float
    published_tau_motor_ms: float
    published_tau_receiver_ms: float

    def vector(self):
        return np.array(
            [
                self.k_gs_pn_nm,
                self.k_joint_pn_nm,
                self.resting_open_probability,
                self.delta_nm,
                self.friction_1e9_kg_s * 1e-3,
                self.motor_friction_1e9_kg_s * 1e-3,
                self.mass_1e12_kg * 1e-3,
                self.gating_swing_nm,
                self.feedback_force_pn,
            ]
        )


# Direct transcription, Tables S1/S2. N counts fitted channels, NOT connectome neurons.
SOURCE_FITS = tuple(
    TransducerParameters(i + 1, *row)
    for i, row in enumerate(
        [
            (0.037, 0.040, 0.38, 0.50, 223, 2653, 5.07, 99.0, 3.57, 1290, 101, 38.0, 9.30, 1.48),
            (0.017, 0.032, 0.25, 0.58, 210, 1221, 7.13, 10.8, 2.70, 1346, 41.8, 10.6, 4.00, 0.76),
            (0.087, 0.084, 0.16, 0.50, 239, 6823, 14.8, 42.8, 6.99, 1310, 227, 36.2, 7.32, 0.95),
            (0.038, 0.053, 0.29, 0.50, 190, 2033, 6.94, 117, 5.44, 1112, 85.3, 24.4, 8.23, 1.57),
            (0.016, 0.026, 0.38, 0.50, 208, 1006, 6.25, 64.4, 4.80, 1202, 41.4, 15.9, 5.40, 1.54),
            (0.026, 0.017, 0.21, 0.50, 461, 6989, 2.51, 243, 1.93, 2329, 134, 28.3, 11.7, 1.54),
            (0.036, 0.037, 0.24, 0.50, 246, 3031, 7.47, 90.0, 4.39, 1374, 100, 24.4, 8.48, 1.18),
        ]
    )
)


def _finite_vector(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or not np.all(np.isfinite(x)):
        raise ValueError("Expected a finite one-dimensional physical signal")
    return x


@njit
def _probability(z, p0, delta):
    logit = np.log(p0 / (1 - p0)) + z / delta
    if logit >= 0:
        return 1 / (1 + np.exp(-logit))
    exponential = np.exp(logit)
    return exponential / (1 + exponential)


@njit
def _rhs(state, force, p):
    k, kj, p0, delta, drag, motor_drag, mass, swing, feedback = p
    x, v, a, posterior = state
    za, zp = x - a, -x - posterior
    da = _probability(za, p0, delta) - p0
    dp = _probability(zp, p0, delta) - p0
    spring_a, spring_p = k * (za - swing * da), k * (zp - swing * dp)
    return np.array(
        [
            v,
            (-spring_a + spring_p - drag * v - kj * x + force) / mass,
            (spring_a + feedback * da) / motor_drag,
            (spring_p + feedback * dp) / motor_drag,
        ]
    )


@njit
def _forced_steps(force, state, p, dt_ms):
    out = np.empty((len(force), 7))
    for i in range(len(force)):
        pa = _probability(state[0] - state[2], p[2], p[3])
        pp = _probability(-state[0] - state[3], p[2], p[3])
        out[i, :4] = state
        out[i, 4], out[i, 5] = pa, pp
        out[i, 6] = max(pa - p[2], 0) + max(pp - p[2], 0)
        f = force[i]
        a = _rhs(state, f, p)
        b = _rhs(state + dt_ms * a / 2, f, p)
        c = _rhs(state + dt_ms * b / 2, f, p)
        d = _rhs(state + dt_ms * c, f, p)
        state = state + dt_ms * (a + 2 * b + 2 * c + d) / 6
    return out, state


class ForceTransducer:
    """Deterministic source eqs 3-6, NOT a stochastic free-fluctuation simulation.

    Input pN; columns x_nm, velocity_nm_ms, motor_a_nm, motor_p_nm,
    open_a, open_p, excess_open_probability. Anterior/posterior are mechanical
    populations within ONE antenna, not left/right ears or MaleCNS JO subtypes.
    """

    def __init__(self, parameters, dt_seconds=1 / 48000):
        if not isinstance(parameters, TransducerParameters) or parameters not in SOURCE_FITS:
            raise ValueError("Choose one of the seven transcribed source parameter sets")
        if not np.isfinite(dt_seconds) or not 0 < dt_seconds <= 1 / 48000:
            raise ValueError("Use a positive receiver timestep at most 1/48000 second")
        self.parameters, self.dt_seconds = parameters, dt_seconds
        self.p = parameters.vector()
        self.reset()

    def reset(self):
        self.state = np.zeros(4)

    def process(self, force_pn):
        force = _finite_vector(force_pn)
        out, state = _forced_steps(force, self.state, self.p, self.dt_seconds * 1000)
        if not np.all(np.isfinite(out)) or not np.all(np.isfinite(state)):
            raise FloatingPointError("Force transducer diverged; state not committed")
        self.state = state
        return out

    def jacobian(self):
        k, kj, p0, delta, drag, motor_drag, mass, swing, feedback = self.p
        slope = p0 * (1 - p0) / delta
        spring = k * (1 - swing * slope)
        motor = (spring + feedback * slope) / motor_drag
        return np.array(
            [
                [0, 1, 0, 0],
                [-(2 * spring + kj) / mass, -drag / mass, spring / mass, -spring / mass],
                [motor, 0, -motor, 0],
                [-motor, 0, 0, -motor],
            ]
        )

    def displacement_transfer(self, frequency_hz):
        """Independent linearization: nm/pN, s=+i omega, physical clock in ms."""
        s = 2j * np.pi * frequency_hz / 1000
        forcing = np.array([0, 1 / self.p[6], 0, 0])
        return np.linalg.solve(s * np.eye(4) - self.jacobian(), forcing)[0]

    def derived_constants(self):
        p = self.parameters
        return {
            "tau_receiver_ms": float(2 * self.p[6] / self.p[4]),
            "tau_motor_ms": float(-1 / self.jacobian()[2, 2]),
            "thermal_energy_pn_nm_from_eq2": p.k_gs_pn_nm
            * p.gating_swing_nm
            * p.delta_nm
            / p.channels_per_population,
            "largest_eigenvalue_real_per_ms": float(np.linalg.eigvals(self.jacobian()).real.max()),
        }

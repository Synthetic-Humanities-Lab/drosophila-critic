"""Stoop et al. 2006 Fig. 3 oscillator; NOT a healthy forced-sound receiver.

x'' = -Pn(x) x' - Pm(x), x in mm, time in seconds.
The source coefficients were fitted to DMSO-induced self-oscillation.
No air-velocity-to-force coefficient is supplied or invented here.
"""

import numpy as np
from numba import njit

PARAMETER_SET = "stoop-2006-figure3-dmso-20min"
DAMPING = (-8.602e2, -9.481e5, 4.811e10)
RESTORING = (31.98, 2.023e6, -7.85e8, -7.474e13, 1.501e15, 7.488e20)


@njit
def _derivative(x, v):
    p = DAMPING[0] + x * (DAMPING[1] + x * DAMPING[2])
    q = RESTORING[-1]
    for coefficient in RESTORING[-2::-1]:
        q = coefficient + x * q
    return v, -p * v - q


@njit
def _integrate(n, dt, x, v):
    out = np.empty((n, 2))
    for i in range(n):
        # Save the state at interval start, then advance one RK4 step.
        out[i, 0], out[i, 1] = x, v
        a, b = _derivative(x, v)
        c, d = _derivative(x + dt * a / 2, v + dt * b / 2)
        e, f = _derivative(x + dt * c / 2, v + dt * d / 2)
        g, h = _derivative(x + dt * e, v + dt * f)
        x += dt * (a + 2 * c + 2 * e + g) / 6
        v += dt * (b + 2 * d + 2 * f + h) / 6
    return out, x, v


class SourceOscillator:
    def __init__(self, dt=1 / 48000):
        if not np.isfinite(dt) or not 0 < dt <= 1 / 48000:
            raise ValueError("Use a positive step no greater than 1/48000 second")
        self.dt = dt
        self.reset()

    def reset(self):
        # Explicit numerical initial condition; not the source experiment's initial state.
        self.x = self.v = 0.0

    def advance(self, samples):
        if not isinstance(samples, int) or samples < 0:
            raise ValueError("Sample count must be a nonnegative integer")
        out, x, v = _integrate(samples, self.dt, self.x, self.v)
        if not np.all(np.isfinite(out)) or not np.isfinite(x + v):
            raise FloatingPointError("Oscillator diverged; state was not committed")
        self.x, self.v = x, v
        return out

"""Clemens et al. 2018 S -> full-wave R -> D motif, in explicit model units.

Normalized exponential filters are our discretization convention. The article
prints an unnormalized integral; source code/data are available on request.
Consequently this is a motif implementation, not a claimed numerical reproduction.
"""

from dataclasses import dataclass

import numpy as np
from numba import njit


@dataclass(frozen=True)
class AdaptationConfig:
    tau_sub_seconds: float = 0.030
    tau_div_seconds: float = 0.050
    sigma_div: float = 1e-4
    dt_seconds: float = 1 / 48000

    def __post_init__(self):
        values = [self.tau_sub_seconds, self.tau_div_seconds, self.sigma_div, self.dt_seconds]
        if not np.all(np.isfinite(values)) or min(values) <= 0:
            raise ValueError("Adaptation parameters must be finite and positive")


@njit
def _filter(x, mean, level, a, b, floor):
    out = np.empty_like(x)
    for i in range(len(x)):
        mean = a * mean + (1 - a) * x[i]
        rectified = abs(x[i] - mean)
        level = b * level + (1 - b) * rectified
        out[i] = rectified / (floor + level)
    return out, mean, level


class Adaptation:
    def __init__(self, config=AdaptationConfig()):
        self.config = config
        self.reset()

    def reset(self):
        self.mean = self.level = 0.0

    def process(self, displacement_model_units):
        x = np.asarray(displacement_model_units, dtype=float)
        if x.ndim != 1 or not np.all(np.isfinite(x)):
            raise ValueError("Expected finite displacement in explicit model units")
        c = self.config
        out, mean, level = _filter(
            x,
            self.mean,
            self.level,
            np.exp(-c.dt_seconds / c.tau_sub_seconds),
            np.exp(-c.dt_seconds / c.tau_div_seconds),
            1 / c.sigma_div,
        )
        if not np.all(np.isfinite(out)):
            raise FloatingPointError("Adaptation diverged; state was not committed")
        self.mean, self.level = mean, level
        return out

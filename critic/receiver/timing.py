"""Experimental timing adapter around upstream FlyBrain.step; weights stay unchanged."""

from collections import deque
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SimulationConfig:
    dt_seconds: float = 0.0005
    propagation_delay_seconds: float = 0.020
    seed: int = 64

    def __post_init__(self):
        if self.dt_seconds not in (0.020, 0.0005, 0.00025):
            raise ValueError("Supported clocks: 20, 0.5, or 0.25 ms")
        if self.propagation_delay_seconds != 0.020:
            raise ValueError("This edition preserves the inherited 20 ms delay")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("Seed must be a nonnegative integer")


class DelayedFlyBrain:
    """Single CPU fly, original step dynamics, explicit spike queue and current integral.

    This is a timing experiment, not a physiological validation. Bernoulli noise
    keeps upstream event-rate scaling; seeds at different clocks are not paired
    realizations. Use noise_hz=0 for controlled numerical comparisons.
    """

    def __init__(self, brain, config=SimulationConfig()):
        if brain.device != "cpu" or brain.batch != 1 or brain.refractory_steps:
            raise ValueError("Timing adapter requires one CPU fly without refractory override")
        if not np.isclose(brain.dt, config.dt_seconds, rtol=0, atol=1e-12):
            raise ValueError("Construct FlyBrain with the configured timestep first")
        self.brain, self.config = brain, config
        self.delay_steps = round(config.propagation_delay_seconds / config.dt_seconds)
        self.reset()

    def reset(self):
        self.brain.reset(self.config.seed)
        self.pending = deque(np.empty(0, dtype=np.int64) for _ in range(self.delay_steps))

    def step(self, current_drives=()):
        """Drives are (indices, abstract voltage/second), never semantic features.

        Integrate constant current over this step including membrane leakage. Synaptic
        spike impulses retain upstream amplitude; they are never multiplied by dt.
        """
        b = self.brain
        injections = []
        factor = b.tau * -np.expm1(-b.dt / b.tau)
        for indices, rate in current_drives:
            indices = np.asarray(indices)
            if indices.ndim != 1 or indices.dtype.kind not in "iu":
                raise ValueError("Target indices must be an integer vector")
            if np.any(indices < 0) or np.any(indices >= b.n):
                raise ValueError("Target indices outside connectome")
            if np.ndim(rate) != 0 or not np.isfinite(rate) or rate < 0:
                raise ValueError("Drive must be a finite nonnegative scalar current")
            injections.append((indices, float(rate) * factor))
        b.fired = self.pending.popleft()
        fired = b.step(inject=injections)
        self.pending.append(fired.copy())
        return fired

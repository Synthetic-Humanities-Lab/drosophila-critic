"""Inference-only port of the authors' saved locomotion policies.

The first layer uses layer normalization and tanh; remaining hidden layers use
ELU. The mean head is linear. No parameters are fitted by this project.
"""

import numpy as np


class FrozenBodyPolicy:
    def __init__(self, variables, keys):
        self.variables = [np.asarray(v, dtype=np.float32) for v in variables]
        self.keys = sorted(keys)

    def __call__(self, observation):
        x = np.concatenate([np.asarray(observation[k]).reshape(-1) for k in self.keys])
        x = x.astype(np.float32)
        v = self.variables
        x = x @ v[1] + v[0]
        mean = np.mean(x)
        variance = np.mean(np.square(x - mean))
        x = np.tanh((x - mean) / np.sqrt(variance + np.float32(1e-5)) * v[3] + v[2])
        for i in range(4, len(v) - 4, 2):
            x = x @ v[i + 1] + v[i]
            x = np.where(x >= 0, x, np.expm1(np.minimum(x, 0)))
        return x @ v[-3] + v[-4]

    @classmethod
    def load(cls, path):
        with np.load(path) as data:
            return cls([data[f"v{i}"] for i in range(int(data["n"]))], data["keys"].tolist())

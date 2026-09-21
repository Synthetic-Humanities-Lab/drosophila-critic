"""Energy-balanced local gain edits. Waveform and time intervals only."""

import numpy as np


def variants(x, rate, intervals):
    x = np.asarray(x, float)
    windows = []
    for start, end in intervals:
        a, b = round(start * rate), round(end * rate)
        ramp = round(0.08 * rate)
        if a < 0 or b > len(x) or b - a < 2 * ramp:
            raise ValueError("Target must fit the recording and its ramps")
        w = np.zeros(len(x))
        w[a:b] = 1
        edge = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, ramp))
        w[a : a + ramp] = edge
        w[b - ramp : b] = edge[::-1]
        windows.append(w)
    w1, w2 = windows
    if np.any(w1 * w2):
        raise ValueError("Targets must not overlap")
    e1, e2 = [np.sum(x * x * w) for w in windows]
    if min(e1, e2) <= 0:
        raise ValueError("Targets must contain sound")
    q = 0.45 * min(e1, e2)
    outputs = {}
    for name, sign in [("earlier", 1), ("later", -1)]:
        gain = np.sqrt(1 + sign * q * w1 / e1 - sign * q * w2 / e2)
        y = x * gain
        if np.max(np.abs(y)) >= 0.95:
            raise ValueError("Emphasis exceeds the peak ceiling")
        y = np.rint(y * 32768).astype(np.int16).astype(float) / 32768
        if not np.array_equal(y[(w1 + w2) == 0], x[(w1 + w2) == 0]):
            raise ValueError("Off-target PCM changed")
        if abs(np.sqrt(np.mean(y * y)) - np.sqrt(np.mean(x * x))) > 1e-6:
            raise ValueError("RMS match outside quantization tolerance")
        outputs[name] = (y, gain)
    return outputs

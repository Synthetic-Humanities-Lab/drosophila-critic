"""Declared temporal diagnostics; inputs are measured rates, never poem content."""

import numpy as np

from .delivery import paired_stats


def temporal_evidence(paired):
    x = np.asarray(paired, float)
    mean = x.mean(axis=0)
    spread = x.std(axis=0, ddof=1)
    a = x[: len(x) // 2].mean(axis=0)
    b = x[len(x) // 2 :].mean(axis=0)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    cosine = float(np.dot(a, b) / denominator) if denominator else 0.0
    signal = float(np.sqrt(np.mean(mean**2)))
    noise = float(np.sqrt(np.mean(spread**2)))
    return dict(
        mean_trace_rms=signal,
        seed_sd_rms=noise,
        split_half_cosine=cosine,
        criterion_met=bool(signal > noise and cosine > 0.5),
    )


def episodes(paired, dt=0.1):
    x = np.asarray(paired, float)
    width = round(0.5 / dt)
    windows = [(i, x[:, i : i + width].mean(axis=1)) for i in range(0, x.shape[1] - width + 1)]
    windows.sort(key=lambda item: -abs(item[1].mean()))
    chosen = []
    for start, values in windows:
        if all(abs(start * dt - e["start"]) >= 1 for e in chosen):
            chosen.append(
                dict(
                    start=round(start * dt, 3),
                    end=round(start * dt + 0.5, 3),
                    mean=float(values.mean()),
                    sd=float(values.std(ddof=1)),
                    values=values.tolist(),
                    positive=int((values > 0).sum()),
                    negative=int((values < 0).sum()),
                )
            )
        if len(chosen) == 3:
            break
    return sorted(chosen, key=lambda e: e["start"])


def paired_summary(values):
    """Remove arithmetic roundoff far below one spike before counting signs."""
    x = np.asarray(values, float)
    return paired_stats(np.where(np.abs(x) < 1e-12, 0.0, x))

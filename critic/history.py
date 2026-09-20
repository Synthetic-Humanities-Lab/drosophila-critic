"""Matched-history stimuli and factorial contrasts, without textual input."""

import numpy as np

from .temporal import paired_summary, temporal_evidence

GAPS = (0.0, 0.5, 2.0)
CONTRASTS = ("total", "lingering", "after_a", "after_b", "interaction")


def stimuli(samples, rate):
    """Reorder whole two-second PCM blocks; never reverse samples within speech."""
    if rate <= 0 or len(samples) < 8 * rate:
        raise ValueError("Eight seconds of source PCM are required")
    a = samples[: 6 * rate]
    b = np.concatenate(
        [samples[4 * rate : 6 * rate], samples[2 * rate : 4 * rate], samples[: 2 * rate]]
    )
    probe = samples[6 * rate : 8 * rate]
    result = {}
    for gap in GAPS:
        for history, lead in (("a", a), ("b", b)):
            for ending, suffix in (("probe", probe), ("quiet", np.zeros_like(probe))):
                name = f"g{round(gap * 1000)}_{history}_{ending}"
                result[name] = (
                    np.concatenate([lead, np.zeros(round(gap * rate)), suffix]),
                    dict(
                        gap=gap,
                        history=history,
                        ending=ending,
                        probe_start=6 + gap,
                        duration=8 + gap,
                    ),
                )
    return result


def factorial(ap, aq, bp, bq):
    """Cast before subtraction to prevent unsigned spike-count underflow."""
    ap, aq, bp, bq = [np.asarray(x, dtype=np.int64) for x in (ap, aq, bp, bq)]
    if not (ap.shape == aq.shape == bp.shape == bq.shape):
        raise ValueError("Factorial trials must share the probe clock and shape")
    return dict(
        total=bp - ap,
        lingering=bq - aq,
        after_a=ap - aq,
        after_b=bp - bq,
        interaction=(bp - bq) - (ap - aq),
    )


def summarize(rates):
    """Seeds × complete 100 ms bins. Fixed windows, without event selection."""
    x = np.asarray(rates, float)
    if x.ndim != 2 or x.shape[0] != 8 or x.shape[1] != 20:
        raise ValueError("Expected eight seeds and twenty 100 ms probe bins")
    return {
        "early": dict(
            temporal=temporal_evidence(x[:, :5]), mean=paired_summary(x[:, :5].mean(axis=1))
        ),
        "full": dict(temporal=temporal_evidence(x), mean=paired_summary(x.mean(axis=1))),
        "trace": dict(
            time=(np.arange(20) * 0.1).tolist(),
            mean=x.mean(axis=0).tolist(),
            low=x.min(axis=0).tolist(),
            high=x.max(axis=0).tolist(),
            seeds=x.tolist(),
        ),
    }

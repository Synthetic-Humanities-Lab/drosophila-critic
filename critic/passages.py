"""Native-clock passage summaries and external input-only comparators."""

import numpy as np

from critic.temporal import paired_summary

DT = 0.02


def smooth_drive(drive, tau):
    x = np.asarray(drive, float)
    if tau == 0:
        return x.copy()
    if tau < 0:
        raise ValueError("Time constant must be nonnegative")
    out = np.empty_like(x)
    decay = np.exp(-DT / tau)
    state = 0.0
    for i, value in enumerate(x):
        state = decay * state + (1 - decay) * value
        out[i] = state
    return out


def bins(x):
    x = np.asarray(x)
    n = x.shape[-1] // 5 * 5
    return x[..., :n].reshape(*x.shape[:-1], -1, 5).mean(axis=-1)


def fit_gain(drive, response, tau):
    x = bins(smooth_drive(drive, tau))
    y = bins(response).mean(axis=0)
    if len(x) != len(y) or np.dot(x, x) == 0:
        raise ValueError("Calibration requires aligned nonzero input")
    return float(max(0, np.dot(x, y) / np.dot(x, x)))


def score(response, prediction):
    y = bins(response).mean(axis=0)
    p = bins(prediction)
    error = np.mean((y - p) ** 2)
    variance = np.mean((y - y.mean()) ** 2)
    return dict(
        rmse=float(np.sqrt(error)),
        zero_rmse=float(np.sqrt(np.mean(y**2))),
        r2=float(1 - error / variance) if variance else None,
        seed_sd_rms=float(np.sqrt(np.mean(bins(response).std(axis=0, ddof=1) ** 2))),
    )


def interval(start, end, frames):
    a, b = max(0, round(start / DT)), min(frames, round(end / DT))
    if b <= a:
        raise ValueError("Empty passage interval")
    return a, b


def contrast(values):
    result = paired_summary(values)
    result["criterion_met"] = bool(
        abs(result["mean"]) > result["sd"] and max(result["positive"], result["negative"]) >= 7
    )
    return result


def compare_passage(reference, human, ref_window, human_window):
    ra, rb = interval(*ref_window, reference.shape[-1])
    ref_mean = reference[:, ra:rb].mean(axis=1)
    checks = []
    for start_shift in [-0.2, 0, 0.2]:
        for end_shift in [-0.2, 0, 0.2]:
            a, b = interval(
                human_window[0] + start_shift, human_window[1] + end_shift, human.shape[-1]
            )
            checks.append(contrast(human[:, a:b].mean(axis=1) - ref_mean))
    result = checks[4]
    return dict(
        **result,
        boundary_robust=bool(
            all(
                c["criterion_met"] and np.sign(c["mean"]) == np.sign(result["mean"]) for c in checks
            )
        ),
        boundary_mean_range=[min(c["mean"] for c in checks), max(c["mean"] for c in checks)],
        boundary_checks=checks,
    )

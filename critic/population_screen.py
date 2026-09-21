"""Fixed native-time gates for the annotated-population screen."""

import numpy as np

from critic.passages import contrast


def bounds(window, length):
    a = max(0, int(np.ceil(window[0] / 0.1 - 1e-9)))
    b = min(length, int(np.floor(window[1] / 0.1 + 1e-9)))
    if b <= a:
        raise ValueError("No complete bins in window")
    return a, b


def evidence(reference, human, windows, predictions):
    a, b = bounds(windows["reference"], reference.shape[-1])
    raw, residuals, actual = [], {key: [] for key in predictions}, []
    for ds in [-0.2, 0, 0.2]:
        for de in [-0.2, 0, 0.2]:
            c, d = bounds([windows["human"][0] + ds, windows["human"][1] + de], human.shape[-1])
            diff = human[:, c:d].mean(axis=1) - reference[:, a:b].mean(axis=1)
            raw.append(contrast(diff))
            actual.append([c * 0.1, d * 0.1])
            for key, p in predictions.items():
                baseline = p["human"][c:d].mean() - p["reference"][a:b].mean()
                residuals[key].append(contrast(diff - baseline))
    direction = int(np.sign(raw[4]["mean"]))
    all_checks = raw + [c for checks in residuals.values() for c in checks]
    qualifies = bool(
        direction
        and all(c["criterion_met"] and np.sign(c["mean"]) == direction for c in all_checks)
    )
    strength = min(
        abs(c["mean"]) / max(c["sd"], 1e-12) for checks in residuals.values() for c in checks
    )
    return dict(
        raw=raw,
        residuals=residuals,
        direction=direction,
        qualifies=qualifies,
        strength=float(strength),
        reference_bounds=[a * 0.1, b * 0.1],
        human_bounds=actual,
    )


def select_candidates(rows):
    return sorted(
        [r for r in rows if r["evidence"]["qualifies"]],
        key=lambda r: (-r["evidence"]["strength"], r["type"], r["stanza"]),
    )[:5]


def survives(discovery, validation):
    return bool(validation["qualifies"] and validation["direction"] == discovery["direction"])

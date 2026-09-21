"""Reanalyze archived original-fly counts; never rerun or modify the fly."""

import hashlib
import json
from pathlib import Path

import numpy as np

from critic.passage_reading import Passage, ReadingInput, interpret
from critic.passages import DT, bins, compare_passage, fit_gain, interval, score, smooth_drive

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/passages-v5"
V1 = ROOT / "experiments/delivery-v1"
V2 = ROOT / "experiments/temporal-v2"
GROUPS = ["direct JON postsynaptic partners", "descending_neuron"]
TAUS = [0, 0.1, 0.3]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, allow_nan=False, separators=(",", ":")))


def rates(folder, names, seeds, manifest, inventory):
    result = {}
    with np.load(folder / "counts.npz") as p:
        for name in names:
            n = manifest["conditions"][name]["frames"]
            result[name] = {}
            for group in GROUPS:
                j = list(p["group_names"]).index(group)
                size = inventory["groups"][group]["count"]
                result[name][group] = np.array(
                    [
                        (
                            p[f"{name}_{s}_group_counts"][75 : 75 + n, j].astype(np.int64)
                            - p[f"silence_{n}_{s}_group_counts"][75 : 75 + n, j].astype(np.int64)
                        )
                        / (DT * size)
                        for s in seeds
                    ]
                )
    return result


def main():
    old, manifest = read(V1 / "manifest.json"), read(V2 / "manifest.json")
    inventory = read(ROOT / "docs/population-inventory.json")
    for folder, file in [(V1, "comparison.json"), (V2, "confirmation.json")]:
        if sha(folder / "counts.npz") != read(folder / file)["counts_sha256"]:
            raise ValueError("Source count archive changed")
    calibration = rates(V1, ["reference"], range(64, 72), old, inventory)["reference"][GROUPS[0]]
    observed = rates(V2, ["reference", "human"], range(101, 109), manifest, inventory)
    drives = {}
    sources = [
        V1 / "counts.npz",
        V2 / "counts.npz",
        V1 / "manifest.json",
        V2 / "manifest.json",
        ROOT / "docs/population-inventory.json",
        OUT / "PROTOCOL.md",
    ]
    for name in observed:
        path = V2 / f"{name}-encoding.json"
        fs = read(path)
        if name == "reference":
            calibration_input = V1 / "reference/encoding.json"
            if read(calibration_input) != fs:
                raise ValueError("Calibration and evaluation reference inputs differ")
            sources.append(calibration_input)
        if (
            hashlib.sha256(json.dumps(fs, sort_keys=True).encode()).hexdigest()
            != manifest["conditions"][name]["input_hash"]
        ):
            raise ValueError("Input hash mismatch")
        audio = V1 / name / "audio.wav"
        if sha(audio) != manifest["conditions"][name]["audio_sha256"]:
            raise ValueError("Audio hash mismatch")
        drives[name] = np.array([f["injected_voltage"] for f in fs])
        sources += [path, audio]
    models, predictions = {}, {}
    for tau in TAUS:
        key = str(tau)
        gain = fit_gain(drives["reference"], calibration, tau)
        predictions[key] = {n: gain * smooth_drive(x, tau) for n, x in drives.items()}
        models[key] = dict(
            tau=tau,
            gain=gain,
            scores={n: score(observed[n][GROUPS[0]], p) for n, p in predictions[key].items()},
        )
    passages = []
    for number, first in enumerate([1, 6, 11, 16, 21], 1):
        windows, performances = {}, {}
        for name in observed:
            lines = {line["line"]: line for line in manifest["conditions"][name]["lines"]}
            windows[name] = [lines[first]["start"], lines[first + 3]["end"]]
            a, b = interval(*windows[name], len(drives[name]))
            performances[name] = dict(
                start=a * DT,
                end=b * DT,
                duration=(b - a) * DT,
                mean_drive=float(drives[name][a:b].mean()),
                integrated_drive=float(drives[name][a:b].sum() * DT),
                downstream_rates=observed[name][GROUPS[0]][:, a:b].mean(axis=1).tolist(),
                excess_spikes_per_neuron=(
                    observed[name][GROUPS[0]][:, a:b].sum(axis=1) * DT
                ).tolist(),
            )
        comparisons = {
            g: compare_passage(
                observed["reference"][g],
                observed["human"][g],
                windows["reference"],
                windows["human"],
            )
            for g in GROUPS
        }
        residuals = {
            k: compare_passage(
                observed["reference"][GROUPS[0]] - p["reference"],
                observed["human"][GROUPS[0]] - p["human"],
                windows["reference"],
                windows["human"],
            )
            for k, p in predictions.items()
        }
        passages.append(
            dict(
                number=number,
                lines=[first, first + 3],
                performances=performances,
                comparisons=comparisons,
                residuals=residuals,
            )
        )
    summary = ReadingInput(
        passages=[
            Passage(
                number=p["number"],
                first_duration=p["performances"]["reference"]["duration"],
                second_duration=p["performances"]["human"]["duration"],
                difference=p["comparisons"][GROUPS[0]]["mean"],
                robust=p["comparisons"][GROUPS[0]]["boundary_robust"],
                residual_robust_all=all(r["boundary_robust"] for r in p["residuals"].values()),
            )
            for p in passages
        ],
        human_baseline_r2=[m["scores"]["human"]["r2"] for m in models.values()],
        descending_robust_count=sum(
            p["comparisons"][GROUPS[1]]["boundary_robust"] for p in passages
        ),
    )
    timeline = {}
    for name in observed:
        y = bins(observed[name][GROUPS[0]])
        timeline[name] = dict(
            dt=0.1,
            mean=y.mean(axis=0).tolist(),
            low=y.min(axis=0).tolist(),
            high=y.max(axis=0).tolist(),
            drive=bins(drives[name]).tolist(),
            predictions={k: bins(p[name]).tolist() for k, p in predictions.items()},
        )
    result = dict(
        version="passages-v5",
        seeds=list(range(101, 109)),
        calibration_seeds=list(range(64, 72)),
        conditions={n: manifest["conditions"][n] for n in observed},
        passages=passages,
        models=models,
        timeline=timeline,
        reading=interpret(summary),
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources},
        analysis_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                Path(__file__),
                ROOT / "critic/passages.py",
                ROOT / "critic/passage_reading.py",
            ]
        },
    )
    save(OUT / "comparison.json", result)
    save(OUT / "interpretation-input.json", summary.model_dump())
    rows = [
        "# Corresponding performances — retrospective passage analysis\n",
        "Uses existing original-fly runs; no new simulations. Human boundaries are approximate. All rates below are human minus synthetic, each relative to its matched silence.\n",
        "| Stanza | Difference Hz/neuron | Seed SD | Positive / negative | Boundary robust | Residual robust: immediate / 0.1s / 0.3s |",
        "|---|---:|---:|---|---|---|",
    ]
    for p in passages:
        c = p["comparisons"][GROUPS[0]]
        rows.append(
            f"| {p['number']} | {c['mean']:+.4f} | {c['sd']:.4f} | {c['positive']} / {c['negative']} | {c['boundary_robust']} | {' / '.join(str(r['boundary_robust']) for r in p['residuals'].values())} |"
        )
    rows += [
        "\n## External input-only baselines\n",
        "| Smoothing seconds | Fitted gain | Human R² | Human RMSE | Zero-predictor RMSE |",
        "|---|---:|---:|---:|---:|",
    ]
    for m in models.values():
        s = m["scores"]["human"]
        rows.append(
            f"| {m['tau']} | {m['gain']:.4f} | {s['r2']:.4f} | {s['rmse']:.4f} | {s['zero_rmse']:.4f} |"
        )
    rows += [
        "\n" + result["reading"]["text"],
        "\n" + result["reading"]["limits"],
        "\nR² describes the ensemble-mean 100 ms trace, not individual fly prediction. Residuals do not isolate connectome causation. Equal RMS does not equal equal dose: the human recording lasts 45.1 s versus 26.17 s and has 10 capped encoder frames. No performance-identity causal claim follows. See PROTOCOL.md and comparison.json for all models, per-seed values and boundary checks.",
    ]
    (OUT / "RESULTS.md").write_text("\n".join(rows) + "\n")
    print("\n".join(rows))


if __name__ == "__main__":
    main()

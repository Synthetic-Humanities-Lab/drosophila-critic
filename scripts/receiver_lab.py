"""Reproduce source components and audit experimental clocks, without poem neural claims."""

import argparse
import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from critic.receiver import VERSION
from critic.receiver.acoustics import ReceiverConfig, particle_velocity, prepare_waveform
from critic.receiver.adaptation import Adaptation, AdaptationConfig
from critic.receiver.mechanics import DAMPING, PARAMETER_SET, RESTORING, SourceOscillator

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/receiver-v2"
RAW = ROOT / "results/receiver-v2"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def summary(x):
    return {"rms": float(np.sqrt(np.mean(x**2))), "peak": float(np.max(np.abs(x)))}


def components():
    traces, reports = {}, {}
    for hz in (48000, 96000, 192000):
        traces[hz] = SourceOscillator(1 / hz).advance(hz)
    for hz in (48000, 96000):
        coarse, fine = traces[hz][hz // 2 :], traces[hz * 2][hz::2]
        errors = {}
        for j, name in enumerate(["displacement_mm", "velocity_mm_s"]):
            a, b = summary(coarse[:, j]), summary(fine[:, j])
            errors[name] = {k: abs(a[k] - b[k]) / max(b[k], 1e-15) for k in a}
        reports[str(hz)] = {
            "relative_summary_errors": errors,
            "pass_2_percent": all(v < 0.02 for group in errors.values() for v in group.values()),
        }
    np.savez_compressed(RAW / "oscillator.npz", **{f"hz_{k}": v for k, v in traces.items()})
    samples = 48000
    x = np.ones(samples)
    step = Adaptation().process(x)
    t = np.arange(samples) / 48000
    # Explicit arbitrary model-unit scale, not millimetres or fitted receptor current.
    carrier = np.sin(2 * np.pi * 200 * t) * 1e5
    levels = np.where(t < 0.5, 1, 2)
    adapted = Adaptation().process(carrier * levels)
    np.savez_compressed(RAW / "adaptation.npz", input_model_units=carrier * levels, output=adapted)
    return {
        "mechanics": {
            "parameter_set": PARAMETER_SET,
            "source": "https://doi.org/10.1007/s00249-006-0059-5",
            "damping_coefficients_ascending": DAMPING,
            "restoring_coefficients_ascending": RESTORING,
            "initial_state": [0, 0],
            "integrator": "RK4; interval-start samples",
            "convergence": reports,
            "steady_velocity_mm_s": summary(traces[48000][24000:, 1]),
            "interpretation": "Numerical source-equation reproduction only; DMSO self-oscillation.",
            "healthy_forced_response_validated": False,
        },
        "adaptation": {
            "source": "https://doi.org/10.1038/s41467-017-02453-9",
            "config": asdict(AdaptationConfig()),
            "filter_convention": "unit-DC-gain exponential; post-update output",
            "rectification": "full wave",
            "input_units": "arbitrary model units; physical scale unresolved",
            "constant_offset_final_over_initial": float(step[-1] / step[0]),
            "intensity_step_pre_mean": float(adapted[19200:24000].mean()),
            "intensity_step_early_mean": float(adapted[24000:24480].mean()),
            "intensity_step_late_mean": float(adapted[-4800:].mean()),
            "source_numerical_reproduction_validated": False,
        },
        "oscillator_plot": traces[48000][24000:26400:8].tolist(),
    }


def recordings():
    records = {}
    c = ReceiverConfig()
    for name in ("reference", "human"):
        path = ROOT / "experiments/delivery-v1" / name / "audio.wav"
        rate, original = wavfile.read(path)
        if original.dtype != np.int16:
            raise ValueError("Expected archived PCM16 level-matched recordings")
        x, processing = prepare_waveform(original.astype(float) / 32768, rate, c)
        field = particle_velocity(x, c)
        target = RAW / f"{name}-field.npz"
        np.savez_compressed(target, waveform=x, particle_velocity_xy_mm_s=field)
        records[name] = {
            "original": str(path.relative_to(ROOT)),
            "original_sha256": sha(path),
            "processed_trace": str(target.relative_to(ROOT)),
            "processed_trace_sha256": sha(target),
            "processing": processing,
            "virtual_calibration": asdict(c),
            "particle_velocity_mm_s": summary(field[:, 0]),
            "neural_response": None,
            "status": "Local acoustic field only; no antennal or neural inference",
        }
    return records


def identities():
    with np.load(ROOT / "data/brain.npz") as p:
        mask = np.char.startswith(p["cell_type"].astype(str), "JO-")
        return [
            {
                "body_id": str(body),
                "cell_type": str(kind),
                "side": str(side),
                "legacy_injected": str(kind).startswith(("JO-A", "JO-B")),
                "v2_physiological_mapping": "unresolved; no subtype tuning assigned",
            }
            for body, kind, side in zip(p["ids"][mask], p["cell_type"][mask], p["side"][mask])
        ]


def neural_pilot():
    from critic.config import DATA
    from critic.receiver.timing import DelayedFlyBrain, SimulationConfig
    from critic.simulation import SimulationRunner

    runner = SimulationRunner()
    b = runner.brain
    weights_before = hashlib.sha256(b.weights.tobytes()).hexdigest()
    rows = []
    for dt in (0.020, 0.0005, 0.00025):
        b.dt = dt
        b.tonic = type(b).tonic * -np.expm1(-dt / b.tau) / -np.expm1(-0.020 / b.tau)
        b.decay = np.float32(np.exp(-dt / b.tau))
        for noise in (0.0, 1.2):
            b.noise_hz = noise
            for stimulus in (False, True):
                config = SimulationConfig(dt_seconds=dt)
                adapter = DelayedFlyBrain(b, config)
                counts = []
                spike_digest = hashlib.sha256()
                start = time.monotonic()
                # This is a clock diagnostic current, not receptor output.
                # Equivalent to 0.4 legacy voltage increment at 20 ms.
                current = 0.4 / (b.tau * -np.expm1(-0.020 / b.tau))
                for i in range(round(0.5 / dt)):
                    active = stimulus and 0.2 <= round(i * dt, 9) < 0.3
                    fired = adapter.step([(runner.ear, current)] if active else [])
                    spike_digest.update(np.asarray([len(fired)], dtype="<i8").tobytes())
                    spike_digest.update(np.asarray(fired, dtype="<i8").tobytes())
                    counts.append(
                        [len(fired)]
                        + [int(mask[fired].sum()) for mask in runner.group_masks.values()]
                    )
                legacy_equal = None
                if dt == 0.020:
                    b.reset(config.seed)
                    legacy_digest = hashlib.sha256()
                    for i in range(25):
                        active = stimulus and 10 <= i < 15
                        fired = b.step(inject=[(runner.ear, 0.4)] if active else [])
                        legacy_digest.update(np.asarray([len(fired)], dtype="<i8").tobytes())
                        legacy_digest.update(np.asarray(fired, dtype="<i8").tobytes())
                    legacy_equal = legacy_digest.hexdigest() == spike_digest.hexdigest()
                    if not legacy_equal:
                        raise RuntimeError("20 ms adapter differs from unmodified upstream step")
                counts = np.asarray(counts)
                filename = f"clock-{dt}-{noise}-{'pulse' if stimulus else 'silence'}.npz"
                np.savez_compressed(RAW / filename, counts=counts, dt=dt)
                row = {
                    "legacy_exact_spike_reproduction": legacy_equal,
                    "spike_sha256": spike_digest.hexdigest(),
                    "configuration": asdict(config),
                    "noise_hz": noise,
                    "stimulus": "100 ms abstract current pulse" if stimulus else "silence",
                    "drive_voltage_per_second": current if stimulus else 0,
                    "runtime_seconds": time.monotonic() - start,
                    "total_spikes": counts.sum(axis=0).tolist(),
                    "groups": ["global", *runner.groups],
                    "trace": f"results/receiver-v2/{filename}",
                    "trace_sha256": sha(RAW / filename),
                    "window": "0.2s initial baseline, 0.1s stimulus, 0.2s tail; no warmup",
                }
                rows.append(row)
                print(
                    f"Clock {dt}s, noise {noise}, pulse {stimulus}: {row['runtime_seconds']:.1f}s",
                    flush=True,
                )
    unchanged = weights_before == hashlib.sha256(b.weights.tobytes()).hexdigest()
    if not unchanged:
        raise RuntimeError("Timing experiment mutated connectome weights")
    return {
        "status": "engineering pilot only; not a timestep-equivalence or biological validation",
        "data_sha256": {name: sha(DATA / name) for name in ("brain.npz", "weights.npz")},
        "runtime_weights_sha256": weights_before,
        "weights_unchanged": unchanged,
        "source_sha256": runner.source_hashes,
        "noise_comparison": "Noisy runs are not draw-matched across timesteps; one seed is descriptive only",
        "runs": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--neural-pilot", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True, parents=True)
    RAW.mkdir(exist_ok=True, parents=True)
    report = {
        "version": VERSION,
        "status": "experimental components; production coupling blocked",
        "gates": {
            "healthy_forced_mechanics": False,
            "physical_displacement_to_receptor_scale": False,
            "receptor_to_connectome_current": False,
            "fine_clock_neural_validation": False,
        },
        "components": components(),
        "recordings": recordings(),
        "jon_inventory": identities(),
        "neural_pilot": neural_pilot() if args.neural_pilot else None,
    }
    report["implementation_sha256"] = {
        str(path.relative_to(ROOT)): sha(path)
        for path in sorted((ROOT / "critic/receiver").glob("*.py"))
    }
    report["implementation_sha256"]["scripts/receiver_lab.py"] = sha(Path(__file__))
    (OUT / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(OUT / "report.json")


if __name__ == "__main__":
    main()

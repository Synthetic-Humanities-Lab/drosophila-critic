"""Source-parameter audit and physical-response diagnostics; no invented neural gain."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from critic.receiver.acoustics import ReceiverConfig, particle_velocity, prepare_waveform
from critic.receiver.healthy import SOURCE_FITS, ForceTransducer, SoundTransfer, SoundTransferConfig

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/receiver-v2"
RAW = ROOT / "results/receiver-calibration"
RATE = 48000
# Set before poem calculations: source consistency, not an interesting poem outcome.
SELECTED = SOURCE_FITS[6]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


def parameter_audit():
    rows = []
    for p in SOURCE_FITS:
        d = ForceTransducer(p).derived_constants()
        error = abs(d["tau_motor_ms"] / p.published_tau_motor_ms - 1)
        rows.append(
            {
                "parameters": asdict(p),
                "derived": d,
                "motor_time_relative_discrepancy": error,
                "motor_time_within_5_percent": error < 0.05,
            }
        )
    # Diagnose an apparent transcription/layout problem; do not use swapped values.
    swap = []
    for i, other in [(0, 5), (5, 0)]:
        calculated = rows[i]["derived"]["tau_motor_ms"]
        alternative = (
            calculated
            * SOURCE_FITS[other].motor_friction_1e9_kg_s
            / SOURCE_FITS[i].motor_friction_1e9_kg_s
        )
        swap.append(
            {
                "fly": i + 1,
                "hypothesis": "exchange motor friction values for flies 1 and 6 only",
                "hypothetical_tau_motor_ms": alternative,
                "published_tau_motor_ms": SOURCE_FITS[i].published_tau_motor_ms,
                "applied": False,
            }
        )
    return {
        "fits": rows,
        "unapplied_transposition_hypothesis": swap,
        "selected_fit": SELECTED.fly,
        "selection_reason": "symmetric rest; receiver and motor relaxation times agree within 2% with Table S2; chosen before poem processing",
    }


def source_diagnostics():
    t = np.arange(RATE // 2) / RATE
    frequencies = [100, 200, 300, 394, 400, 600, 1000, 1500]
    tones = []
    for f in frequencies:
        air = np.sqrt(2) * 0.5 * np.sin(2 * np.pi * f * t)
        model = SoundTransfer()
        out = model.process(air)
        observed = rms(out[RATE // 4 :, 1] / 1e6) / rms(air[RATE // 4 :])
        analytic = abs(model.velocity_transfer(f))
        tones.append(
            {
                "frequency_hz": f,
                "air_velocity_rms_mm_s": 0.5,
                "displacement_rms_nm": rms(out[RATE // 4 :, 0]),
                "velocity_gain": observed,
                "analytic_gain": analytic,
                "relative_gain_error": abs(observed / analytic - 1),
            }
        )
    force_rows = []
    traces = {}
    for f in [100, 200, 400, 600, 1000]:
        for amplitude in [0.01, 1.0, 10.0]:
            force = amplitude * np.cos(2 * np.pi * f * t)
            model = ForceTransducer(SELECTED)
            out = model.process(force)
            stable = out[RATE // 4 :]
            times = t[RATE // 4 :]
            gain = abs(2 * np.mean(stable[:, 0] * np.exp(-2j * np.pi * f * times))) / amplitude
            force_rows.append(
                {
                    "frequency_hz": f,
                    "force_peak_pn": amplitude,
                    "displacement_fundamental_gain_nm_pn": gain,
                    "small_signal_gain_nm_pn": abs(model.displacement_transfer(f)),
                    "mean_excess_open_probability": float(stable[:, 6].mean()),
                    "max_excess_open_probability": float(stable[:, 6].max()),
                }
            )
            traces[f"force_{f}_{amplitude}"] = out
    np.savez_compressed(RAW / "force-diagnostics.npz", **traces)
    force = 2 * np.sin(2 * np.pi * 200 * t)
    coarse = ForceTransducer(SELECTED).process(force)
    fine = ForceTransducer(SELECTED, 1 / 96000).process(np.repeat(force, 2))[::2]
    errors = {
        name: float(
            np.linalg.norm(coarse[:, j] - fine[:, j]) / max(np.linalg.norm(fine[:, j]), 1e-12)
        )
        for j, name in [(0, "displacement"), (1, "velocity"), (6, "excess_open_probability")]
    }
    return {
        "sound_transfer_tones": tones,
        "force_transduction_tones": force_rows,
        "force_trace_sha256": sha(RAW / "force-diagnostics.npz"),
        "force_step_halving_relative_trajectory_errors": errors,
        "numerical_convergence_pass_2_percent": all(v < 0.02 for v in errors.values()),
        "force_input_convention": "interval-held pN, deterministic eqs 3-6, dt=1/48000 second; refine held input without changing stimulus",
        "force_tone_parameters": asdict(SELECTED),
    }


def constant_force_bridge_audit():
    """Attempt only a real scalar in the linear limit; do not apply it to poems."""
    frequencies = np.array([100, 200, 300, 394, 400, 600, 1000, 1500])
    target = SoundTransfer().velocity_transfer(frequencies)
    rows = []
    for parameters in SOURCE_FITS:
        model = ForceTransducer(parameters)
        velocity_per_force = np.array(
            [model.displacement_transfer(f) * 2j * np.pi * f * 1e-6 for f in frequencies]
        )
        coefficient = max(
            0.0,
            float(
                np.vdot(velocity_per_force, target).real
                / np.vdot(velocity_per_force, velocity_per_force).real
            ),
        )
        predicted = coefficient * velocity_per_force
        error = float(np.linalg.norm(predicted - target) / np.linalg.norm(target))
        rows.append(
            {
                "fly": parameters.fly,
                "fitted_constant_pn_per_mm_s": coefficient,
                "normalized_complex_response_error": error,
                "applied_to_recordings": False,
            }
        )
    return {
        "purpose": "cross-study compatibility diagnostic, not a measured drag calibration",
        "assumption": "F_pN = coefficient * air_velocity_mm_s, frequency-independent real coefficient, linear response limit",
        "frequency_hz": frequencies.tolist(),
        "fits": rows,
        "loss": "unweighted complex least squares; ||prediction-target||_2 / ||target||_2; includes gain and phase",
        "target": "Gopfert-Robert 2002 Fig 2C representative response fit",
        "limitation": "Different specimens and unspecified matching stimulus level; does not reject either source model or test nonlinear finite-level matching",
        "decision": "No fitted coefficient is promoted to a physiological or production calibration",
    }


def process_recordings():
    rows = {}
    for name in ["reference", "human"]:
        source = ROOT / "experiments/delivery-v1" / name / "audio.wav"
        rate, pcm = wavfile.read(source)
        if pcm.dtype != np.int16:
            raise ValueError("Expected archived PCM16")
        waveform, preprocessing = prepare_waveform(pcm.astype(float) / 32768, rate)
        air = particle_velocity(waveform)[:, 0]
        # Single measured projection. No bilateral geometry is inferred here.
        mechanical = SoundTransfer().process(air)
        # Continue through silence for observable decay; no per-chunk state reset.
        model = SoundTransfer()
        model.process(air)
        tail = model.process(np.zeros(RATE // 10))
        archive = RAW / f"{name}-sound-transfer.npz"
        np.savez_compressed(
            archive,
            sample_rate=RATE,
            particle_velocity_mm_s=air,
            displacement_nm=mechanical[:, 0],
            velocity_nm_s=mechanical[:, 1],
            tail_displacement_nm=tail[:, 0],
            tail_velocity_nm_s=tail[:, 1],
        )
        spectrum = abs(np.fft.rfft(waveform)) ** 2
        frequencies = np.fft.rfftfreq(len(waveform), 1 / RATE)
        outside = float(spectrum[(frequencies < 100) | (frequencies > 1500)].sum() / spectrum.sum())
        timeline = []
        for i in range(0, len(air), 4800):
            segment = mechanical[i : i + 4800]
            timeline.append(
                {
                    "time_seconds": i / RATE,
                    "air_rms_mm_s": rms(air[i : i + 4800]),
                    "displacement_rms_nm": rms(segment[:, 0]),
                    "velocity_rms_mm_s": rms(segment[:, 1] / 1e6),
                }
            )
        rows[name] = {
            "source": str(source.relative_to(ROOT)),
            "source_sha256": sha(source),
            "preprocessing": preprocessing,
            "trace": str(archive.relative_to(ROOT)),
            "trace_sha256": sha(archive),
            "air_rms_mm_s": rms(air),
            "displacement_rms_nm": rms(mechanical[:, 0]),
            "velocity_rms_mm_s": rms(mechanical[:, 1] / 1e6),
            "fraction_audio_energy_outside_source_100_1500_hz": outside,
            "timeline": timeline,
            "neural_response": None,
            "reading": None,
            "claim": "Linear measured-fit reference prediction; arbitrary-level speech and out-of-band response are extrapolations, not validated physiology",
        }
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    report = {
        "version": "receiver-calibration-v1",
        "status": "physical source models implemented; complete neural calibration unresolved",
        "sources": {
            "sound_transfer": {
                "doi": "10.1242/jeb.205.9.1199",
                "location": "Figure 2C; example fitted velocity transfer",
                "author_copy": "https://www.researchgate.net/publication/11418850_The_mechanical_basis_ofDrosophilaaudition",
            },
            "transduction": {
                "doi": "10.1016/j.cub.2008.07.095",
                "location": "Supplement eqs 1-9,18,21; Tables S1-S2",
                "url": "https://ars.els-cdn.com/content/image/1-s2.0-S096098220801049X-mmc1.pdf",
                "downloaded_pdf_sha256": "7b78c1a45716e9ee7e693ad667ece3eef476a8cabda89f7e3cdf88e0efbe2a99",
            },
        },
        "sound_transfer_config": asdict(SoundTransferConfig()),
        "virtual_field_config": asdict(ReceiverConfig()),
        "parameter_audit": parameter_audit(),
        "constant_force_bridge_audit": constant_force_bridge_audit(),
        "diagnostics": source_diagnostics(),
        "recordings": process_recordings(),
        "remaining_contracts": [
            "Measured air-velocity to effective force relation for the nonlinear source model; suspension friction is not automatically air drag",
            "Reconciliation of source table inconsistency for fits 1 and 6 before those fits can be preferred",
            "Channel probability to JON generator current/conductance and spiking; fitted N is channels, not MaleCNS neuron identities",
            "Mapping and calibration of physiological JON response to FlyBrain abstract voltage; no unique dimensional conversion exists in upstream model",
            "Fine-clock and stochastic receiver validation; present source reproduction uses published deterministic equations",
        ],
        "production_receiver_changed": False,
    }
    report["implementation_sha256"] = {
        str(path.relative_to(ROOT)): sha(path)
        for path in [ROOT / "critic/receiver/healthy.py", ROOT / "scripts/calibrate_receiver.py"]
    }
    (OUT / "calibration.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("Selected source fit:", SELECTED.fly)
    for name, row in report["recordings"].items():
        print(name, row["air_rms_mm_s"], row["displacement_rms_nm"], row["velocity_rms_mm_s"])
    print(OUT / "calibration.json")


if __name__ == "__main__":
    main()

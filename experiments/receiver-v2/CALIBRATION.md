# Healthy receiver calibration work — 2026-09-21

**Result:** sound-to-motion and force-to-channel source models are operational.
The acoustic-force and channel-to-connectome current calibrations are still open.
No new neural response or literary reading has been generated.

## What changed

`critic/receiver/healthy.py` implements two separate physical models. They are
alternatives/reference components, not stages silently concatenated together.

1. **Sound transfer reference.** Göpfert & Robert (2002), Fig. 2C, supply a
   representative wild-type arista velocity-response fit: 394 Hz resonance,
   Q=1.24, resonant velocity ratio 1.13. We implement its harmonic-oscillator
   transfer using exact interval-held state updates. Air velocity is mm/s;
   outputs are displacement in nm and velocity in nm/s. This fixed linear fit
   does not reproduce the paper's level-dependent tuning. Applying it to speech
   at arbitrary intensity, or outside the measured 100–1500 Hz band, is an
   extrapolation. The report gives out-of-band energy for each recording.
   Source: [paper](https://doi.org/10.1242/jeb.205.9.1199),
   [author-uploaded full text](https://www.researchgate.net/publication/11418850_The_mechanical_basis_ofDrosophilaaudition).

2. **Force-driven active transducer.** Nadrowski, Albert & Göpfert (2008),
   supplementary equations 1–9 and Tables S1/S2, provide physical parameters
   for seven fitted specimens. Our four-state model implements receiver position,
   velocity and two adaptation-motor positions. It calculates anterior/posterior
   channel probabilities and the source-defined excess open probability. These
   are opposing populations within one antenna, not left/right ears or JO-A/B.
   Fitted channel number N must not be mapped onto connectome neuron count.
   Source: [paper](https://doi.org/10.1016/j.cub.2008.07.095),
   [publisher supplement](https://ars.els-cdn.com/content/image/1-s2.0-S096098220801049X-mmc1.pdf),
   [institutional copy](https://discovery.ucl.ac.uk/id/eprint/62147/).

## Implementation choices

The force model uses nm, ms and pN. Thus a table friction value in 10^-9 kg/s
is multiplied by 0.001 to obtain pN ms/nm; a mass in 10^-12 kg is multiplied by
0.001 to obtain pN ms²/nm. The equations are translated about the zero-force
stationary point. This removes unobservable motor-position offsets without
altering channel probability or mechanical response. The invariant feedback
product Fmax*S is read directly from Table S2 rather than reconstructed from
separately rounded parameters.

No arbitrary conversion from displacement to adaptation model units is needed
in this physical transducer. Its gating distance already has units of nm.
We do **not** append the older S→R→D motif: motor adaptation is already present,
and a further variance-adaptation stage needs separate justification/calibration.
The source's deterministic equations 3–6 are used for source reconstruction.
Thermal fluctuations from equations 10–13 are not implemented here. No neural
noise configuration or connectome weights are changed.

## Source consistency finding

Recalculating the motor relaxation time from supplementary equation 18 and the
printed tables yields:

| Source fit | Calculated τa (ms) | Table S2 τa (ms) |
|---|---:|---:|
| 1 | 3.794 | 9.30 |
| 6 | 28.559 | 11.7 |

Exchanging only the two printed motor-friction values produces approximately
9.31 and 11.64 ms, respectively. This suggests a table transposition, but is **not
an established correction**. Both publisher and institutional PDFs contain the
same values. All source values are preserved and the hypothesis is recorded as
unapplied. The other five motor times agree within 5%. Fit 7 is used for tone
comparisons because both its receiver and motor time constants agree within 2%
and its resting probability is symmetric; this choice precedes poem processing.
It is a literature specimen parameter set, not a simulator seed or MaleCNS subject.

## Checks and actual results

Tests compare the physical force solver against SciPy's independent DOP853
integrator for every fit, verify the analytic Jacobian by finite differences,
and check chunk continuity, reset, silence, sign symmetry, probability bounds,
and step-halving. The sound reference reproduces the analytic magnitude/phase
response including the known sampling hold. Numerical agreement is not an
independent validation against raw biological measurements.

Equal-RMS air tones (0.5 mm/s) at 200 and 600 Hz produce approximately 217 and
102 nm RMS displacement in the linear reference. In the separate force model,
equal 1 pN peak tones produce different channel-probability trajectories. This
shows spectral discrimination in these source equations; it does not establish
measured fly experience or an end-to-end neural response.

The archived, level-matched poem recordings were resampled to 48 kHz without
renormalization. Resampling produces a small RMS difference, which is recorded.
Both use the same virtual calibration and sound-transfer parameters:

| Recording | Air RMS (mm/s) | Displacement RMS (nm) | Vibration velocity RMS (mm/s) |
|---|---:|---:|---:|
| Synthetic reference | 0.25004 | 91.19 | 0.17715 |
| Human performance | 0.25009 | 84.29 | 0.18782 |

These are model predictions conditional on a limited linear reference. The
performances differ in spectrum and timing as well as duration. Neither is
ranked as stronger overall. No force-model channel trajectory is attributed to
these poems, because that requires an additional calibration.

## What calibration still requires

- **Air → force:** a measured frequency/level-dependent relation between local
  air motion and effective forcing for the active model, or a jointly fitted
  acoustic transfer. Its fitted receiver friction includes suspension effects;
  equating it with air drag would invent a calibration. Combining the 2002
  reference with the 2008 active amplifier in series would risk double counting.
- **Channels → neural drive:** channel conductance/current and a supported
  population spiking transfer under the same stimulus conditions. The source
  supplies opening probabilities, not a per-MaleCNS-neuron spike train.
- **Neural drive → FlyBrain:** upstream voltage, threshold, tonic and synaptic
  gain are abstract model quantities. A conversion cannot be obtained by unit
  conversion alone. It needs a declared physiological response target and an
  explicitly fitted input adapter, with held-out responses for validation.
  None of this requires changing connectome weights.

A separate, clearly named engineering gain could support sensitivity experiments,
but it would not close physiological calibration. We have not selected one to
manufacture a convincing poem result. Raw waveform text never enters either
physical model; no interpretation layer runs on these diagnostic outputs.

## Reproduction

```sh
PYTHONPATH=. .venv/bin/python scripts/calibrate_receiver.py
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_healthy_receiver.py
.venv/bin/python scripts/export_replay.py
```

Public `calibration.json` stores source parameters, numerical diagnostics,
source-table discrepancies, waveform hashes and 100 ms mechanical timelines.
Full-resolution arrays and 100 ms silence tails are retained locally in
`results/receiver-calibration/`. Earlier `report.json` is the unchanged prior
laboratory snapshot, including its historical implementation hashes.

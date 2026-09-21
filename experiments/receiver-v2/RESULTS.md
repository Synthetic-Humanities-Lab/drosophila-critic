# Receiver v2 laboratory — 2026-09-21

This is a component and timing audit, not a new poem comparison.

- The published autonomous oscillator passes successive step-halving checks at
  48/96/192 kHz: steady-state displacement/velocity RMS and peak errors are each
  below 2%. Its source parameters describe DMSO-induced motion, not a calibrated
  healthy sound receiver.
- The adaptation motif rejects a constant offset and exhibits an intensity-step
  transient with subsequent adaptation. Its arbitrary input scale is exposed;
  these checks do not reproduce measured receptor currents.
- Both archived level-matched recordings have been resampled without further
  gain adjustment and converted to a declared virtual air-velocity field. No v2
  antennal or neural trajectory is attributed to either recording.
- All 672 JO-prefix identities are inventoried; 138 match legacy injection.
  No new physiological subtype tuning has been assigned.

## Full-connectome timing pilot

The unmodified upstream step engine is wrapped with an explicit 20 ms spike
propagation queue. At the original 20 ms clock, **all four pilot conditions exactly
reproduce the original spike sequences**, including neuron identities and time bins.
Connectome weights remained identical by checksum.

| Clock | Global silence spikes, noise enabled | Global pulse spikes, noise enabled | Direct downstream spikes, noise-free pulse |
|---|---:|---:|---:|
| 20 ms | 119115 | 118958 | 282 |
| 0.5 ms | 248398 | 251082 | 339 |
| 0.25 ms | 246714 | 249939 | 338 |

Each trial is only 0.5 seconds, with 0.2 seconds initial baseline, a 0.1 second
abstract current pulse (or silence), and 0.2 seconds tail. All noise-free silence
trials emitted zero spikes. Noise-enabled runs use seed 64; random draws are not
paired across clocks. These data show an engineering concern, not an ensemble
estimate or a biological validation. Similar fine-clock totals alone do not verify
their onset timing or complete population trajectories.

The 20 ms model caps each neuron at 50 Hz. Finer clocks change that ceiling and
threshold/reset opportunities even with identical weights and propagation delay.
It would be misleading to present the new timing path as an equivalent version
of the old apparatus without further testing.

## Decision

Keep the new components experimental. Resolve healthy forced mechanics, adaptation
scaling and neural-current coupling before conducting the eight-seed poem study.
No literary interpretation or claim about a fly's experience is produced here.

See `report.json` for parameters, source hashes, local trace hashes, all pilot
conditions, convergence errors and the complete JO identity inventory. Full traces
are retained under the repository's ignored `results/receiver-v2/` directory.

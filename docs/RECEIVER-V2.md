# Auditory receiver v2: experimental component build

Status: **not a validated poem receiver**. Existing readings still use `rms-jon-v1`.
The new code is in `critic/receiver`; it does not change the legacy encoder,
connectome, interpreter, or archived experiments. No v2 literary reading is generated.

## Provisional adapter sensitivity pilot

The [sensitivity protocol](https://synthetic-humanities-lab.github.io/drosophila-critic/experiments/receiver-v2/sensitivity/PROTOCOL.md)
connects the linear sound-transfer reference to original FlyBrain through two
explicit engineering adapters: displacement RMS and velocity RMS, each at three
strengths. Their shared scale is anchored to a reference tone, not fitted to neural
physiology. The full-connectome experiment retains the original 20 ms clock and
noise and compares each input with paired silence. The force/channel model is
not part of this chain. The production gate remains closed.

This pilot tests sensitivity to model choices; it does not resolve physiological
calibration. The frame `rms` in its input JSON means the scaled engineering
equivalent waveform RMS, not raw audio RMS or a receptor firing rate.

## Earlier calibration work

The [healthy receiver calibration report](https://synthetic-humanities-lab.github.io/drosophila-critic/experiments/receiver-v2/CALIBRATION.md)
adds a measured sound-transfer reference and a physically scaled force-to-channel
model. It identifies a likely source-table inconsistency and records mechanical
predictions for both recordings. Acoustic-force and channel-to-neural-current
calibration remain unresolved. The following sections document the initial build.

## Implemented boundaries

- `acoustics.py`: waveform-only mono conversion and polyphase resampling to 48 kHz,
  without gain normalization or compression. Digital RMS 0.1 at 200 Hz represents
  **0.5 mm/s RMS virtual local air velocity**. A frequency-independent gain extends
  that calibration to other frequencies: this is our assumed playback field, not a
  microphone calibration or reconstructed original sound field. XY azimuth is explicit.
  Bilateral axis projection requires explicit caller-supplied angles. There is no
  default anatomical angle and no head-boundary-layer model.
- `mechanics.py`: stateful RK4 implementation of the published polynomial oscillator;
  displacement and velocity are separate. No invented forcing coefficient.
- `adaptation.py`: stateful subtractive adaptation, full-wave rectification and
  divisive adaptation. Input is explicitly **model units**, not disguised millimetres.
- `timing.py`: wraps the original `FlyBrain.step`, retains synaptic impulses and the
  inherited 20 ms propagation delay, integrates constant abstract current with leakage,
  and uses upstream tonic/noise scaling. 20, 0.5 and 0.25 ms are explicit clocks.
- `scripts/receiver_lab.py`: reproducible numerical checks, waveform provenance,
  complete JO-prefix identity inventory, and optional full-connectome timing pilot.
- `require_validated_receiver()`: raises with the unresolved coupling requirements.
  No API route silently substitutes the experimental receiver for legacy readings.

## Source register and limits

[Stoop et al. (2006), equation 2 and Fig. 3](https://doi.org/10.1007/s00249-006-0059-5)
provide quadratic damping and quintic restoring polynomials. Their coefficients
fit a DMSO-induced self-oscillation at 20 minutes. They do **not** supply a healthy,
forced-response calibration. We reproduce the autonomous equation with explicit
zero initial state, x in mm and time in seconds. Passing numerical convergence
cannot make this parameter set appropriate for a healthy fly listening to speech.
The absent mapping from air motion to mechanical force is a blocking requirement.

[Clemens, Ozeri-Engelhard and Murthy (2018), Model of JON adaptation](https://doi.org/10.1038/s41467-017-02453-9)
support the S→R→D arrangement. We expose their illustrative 30/50 ms constants
and sigma=1e-4. Our exponential filter has unit DC gain; the printed integral's
normalization and the physical input scale require reconciliation with source code
or data, available from the authors on request. This is a motif implementation,
not numerical reproduction of their measured compound action potentials. A large
explicit model-unit diagnostic input demonstrates divisive adaptation; it is not
an inferred physical displacement or a fitted JON current.

[Batchelor and Wilson (2019)](https://doi.org/10.1242/jeb.191213)
support bilateral direction-dependent antennal responses, including effects of
head geometry on local air motion. Our geometric projection utility alone does
not reproduce those effects or establish a turning response.

The source populations, experimental conditions and sexes are not automatically
interchangeable with a MaleCNS specimen. No JO subtype gets fabricated tuning.
The inventory includes all 672 JO-prefix identities present in the pinned archive;
138 are selected by the legacy JO-A/JO-B naming convention. Every v2 physiological
mapping remains explicitly unresolved. This inventory is not a new taxonomy.

## Numerical conventions and pilot

Receiver samples are interval-start states; filter outputs are post-update states.
State persists across chunks and resets only on explicit reset. Receiver code has
no poem-text interface, line alignment, semantic features or learned parameters.

The timing pilot uses the full original connectome for 0.5 seconds per run:
0.2 seconds baseline, 0.1 seconds abstract input pulse, 0.2 seconds tail. There is
no additional warmup. The input current integrates to a legacy 0.4 voltage increment
per 20 ms before threshold/reset; it is an engineering stimulus, not an auditory
calibration. Silence and pulse are paired within each timestep and noise setting.
Noise-free trials isolate timing changes; noisy trials use seed 64 and upstream
1.2 Hz Bernoulli events. Identical seed numbers across clocks do not give identical
noise events. These short single-seed trials cannot establish ensemble equivalence.

At finer clocks the per-step firing ceiling also changes. Retaining weights,
membrane time constant, tonic equilibrium and propagation delay does not guarantee
unchanged network dynamics. We record this difference rather than tune it away.
Frozen-weight hashes and source hashes are saved. The pilot never modifies weights.

## Run and inspect

From the repository root, after the normal setup and pinned connectome download:

```sh
PYTHONPATH=. .venv/bin/python scripts/receiver_lab.py --neural-pilot
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_receiver.py
.venv/bin/python scripts/export_replay.py
.venv/bin/python -m http.server 8766 --directory dist
```

Open `/receiver.html`. `experiments/receiver-v2/report.json` contains public results;
`results/receiver-v2/` retains full oscillator, adaptation, processed waveform,
physical-field and clock-count traces. Original level-matched WAVs remain in
`experiments/delivery-v1/{reference,human}/audio.wav`; report hashes identify them.
Omitting `--neural-pilot` writes a components-only report with no neural pilot.
No files are inferred from an earlier run when that option is omitted.

## Gates before new poem experiments

1. Obtain or fit a healthy forced-response mechanical parameter set against
   published response curves, with air-velocity/force units and uncertainty.
   The current DMSO benchmark cannot serve this role.
2. Reconcile adaptation input scaling and kernel convention with source data;
   establish the mechanics/transduction boundary without double amplification.
3. Establish an explicit receptor-to-abstract-current calibration and supported
   JO population mapping. Freeze parameters before testing poem differences.
4. Validate the timing extension on longer baselines and stimulus batteries,
   across noise realizations, including rate saturation and onset timing. The
   short pilot demonstrates why this is necessary.
5. Only then run the paired recordings, eight seeds and duration-matched silence;
   calculate downstream metrics and feed only response summaries to interpretation.

The source check therefore changes the implementation sequence: source components
and a clock audit are operational, but the full v2 sensory chain and poem experiment
remain blocked by identifiable scientific contracts, not by missing interface work.

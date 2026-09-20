# Auditory entry audit — before implementation

Inspected upstream `alextitonis/fly.ai` at commit
`5e931b8dc4856550565c5fa129d3d0c055af3dd1` (2026-09-20).
Sources: `vendor/fly.ai/flytalk.py`, `flybrain/brain.py`,
`flybrain/build.py`, `flybrain/data.py`, and `flybrain/reservoir.py`.

## Exactly what flytalk stimulates

`EAR_PREFIXES = ("JO-A", "JO-B")`. `ear_cells(brain)` finds every distinct
`cell_type` starting with either prefix and passes those types to `brain.cells`.
There is no side restriction and no subtype-specific tuning. Every selected
neuron receives the same scalar extra voltage. The installed data's exact
types, counts and body IDs will be exported to `docs/population-inventory.json`.
The selection is reused by importing upstream `ear_cells`, not approximating it.

## What its song is

`speak` counts spikes from the listed `WING_MN` types, divided into left/right
groups. `sound_of` adds the two counts and subtracts a mean resting count,
clipping negative results to zero. This is a synthetic wing-spike envelope,
not recorded sound or a physical wing-motion model. `run` sets a gain from
the 90th percentile of positive song values so that value reaches `EAR_CAP=0.8`.
`listen` injects `min(gain * heard[s-1], 0.8)` into all selected neurons at the
next step. The one-step delay links sender and receiver simulations; it does
not establish a measured auditory latency. No frequency channels are used.

## Data and modeling seams

MaleCNS supplies neuron identities, cell-type/superclass/side annotations,
connectivity, synapse counts, and predicted neurotransmitter labels.
fly.ai supplies a discrete LIF model, inhibitory-sign assignment, absolute
incoming-weight normalization, tonic drive, stochastic noise, thresholds,
and the JO-A/B selection and common-voltage injection convention. Its defaults
are dt=20 ms, tau=100 ms, gain=3, tonic=0.14, noise probability=1.2*dt per neuron
per step, noise amplitude=0.22, and no refractory period. The reservoir module
also contains trained readouts; those are not used here.

Upstream optionally removes incoming synapses on sensory neurons. We leave
`sensory_input=True`, retaining the entire supplied weight matrix. This also
retains upstream's documented spontaneous/sensory feedback limitations.

## Smallest bridge for human speech

Use one fixed local synthetic voice. Downmix to mono and apply one global
RMS gain, peak-limited, with no gating, compression, linguistic analysis or
frequency weighting. Partition into 20 ms frames (zero-pad the final frame).
Measure frame RMS; inject `min(4 * RMS, 0.8)` equally into upstream's JO-A/B
selection at that frame's simulation step. The fixed gain of 4 is ours, not a
biological calibration. Unlike flytalk, it is not recalibrated per poem.
An audio frame already represents its time interval, so no sender/receiver
delay is added. Record each frame's RMS, sample bounds and injected amount.

This maps an amplitude envelope into a documented anatomical entry point.
It is not a validated model of a fly hearing human speech. In particular,
it discards carrier frequency and does not model particle velocity, antenna
resonance, adaptation, or differential JO-A/B tuning. Frequency specificity
would require evidence and a separate encoder revision, not decorative bands.

Line boundaries may be retained separately for playback alignment. Only PCM
and acoustic frames enter the simulator. Only numerical response summaries
and temporal/line numbers enter interpretation; poem text never does.

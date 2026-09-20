# The Drosophila Critic — method v2

This is a computational artwork and critical apparatus. It is not evidence that
Drosophila understands poetry. The nervous system functions as an instrument.
**RESPONSE** is a measurement of simulated neural activity. **READING** is a
downstream interpretation of those measurements. Neither is a claim about a
living fly's subjective experience.

## From MaleCNS

The MaleCNS v1.0 release supplies neuron identities, connectivity, synapse
counts, cell-type/superclass/side annotations and predicted neurotransmitters.
We use fly.ai's `brain-v1` prebuilt files: 166,700 superclass-annotated neurons
and 25,582,938 directed connections. This is the complete network distributed
by fly.ai, not an assertion that every biological neuron or synapse is known.
File checksums are checked against upstream and saved in each result.

## From fly.ai

Pinned source: [alextitonis/fly.ai at 5e931b8](https://github.com/alextitonis/fly.ai/tree/5e931b8dc4856550565c5fa129d3d0c055af3dd1).
`FlyBrain.step` executes the original LIF dynamics. Synapse-count weights are
signed negative for predicted GABA, glutamate and histamine, then normalized
by each postsynaptic neuron's total absolute input. These transformations,
LIF dynamics and parameters are modeling choices, not direct EM observations.

The original CPU implementation is used without edits. dt=20 ms, tau=100 ms,
gain=3, tonic=0.14, noise amplitude=0.22 with probability 1.2*dt per neuron per
step, threshold=1, reset voltage=0, no refractory period. `sensory_input=True`:
no incoming sensory synapses are removed. All weights remain fixed; their
hash is compared before and after each run. No training, fitted policy or
learned readout is used. Upstream's reservoir training code is never invoked.

The upstream `flytalk.ear_cells` function selects all cell types beginning
JO-A or JO-B, both sides. In these data, there are 138 input neurons in 13
types. Exact names/counts/body IDs and available groups are in
`docs/population-inventory.json`. See `docs/AUDITORY_ENTRY.md`, written before
encoder implementation, for the original wing-spike song encoding and seams.

## From us: voice and transduction

The canonical voice is local Kokoro v1.0 (82M), `af_sarah`, English US,
with speed 1.0, native fixed pitch and no style/voice selection. The ONNX model
and voice bank are checksum-pinned; `kokoro-onnx==0.4.9` and CPU ONNX Runtime
versions are recorded. Synthesis has its own seed 64, reset in a fresh process
for every poem (the model contains stochastic operations). Repeated PCM and
injections were verified identical on this host. Four intra-op threads and
one inter-op thread are fixed. Cross-platform bitwise identity is not promised.
An explicit adapter corrects the wrapper's int32 speed input to the pinned
model's declared float32 type. No learned weights are changed. There is no
API key, browser-selected voice, remote synthesis or LLM.

The original eSpeak provider remains an explicit test/legacy provider; there
is no silent fallback. Saved eSpeak readings retain their original waveform,
voice metadata and method snapshot. Kokoro's phonemizer uses eSpeak internally;
pronunciation data remain entirely inside the TTS boundary.
Lines are separately synthesized, with a fixed 180 ms gap appended to every
line, including the last. Empty lines create an additional gap. Actual PCM
sample boundaries establish line highlighting, with no guessed word timings.
This imposes line-based prosody and may disrupt enjambment; it is a deliberate
standardization choice. Ordinary pronunciation machinery lives inside TTS;
no phonemes, token meanings or other text features cross into the simulator.
Input is ordinary text, not an SSML interface. Upstream leading/trailing silence
trimming is enabled independently for each line; overlong phoneme batches
are rejected rather than silently truncated. Pronunciation is standardized,
not guaranteed correct for every poetic form, name or language.

Audio becomes mono float PCM, scaled once to RMS 0.1 across the whole waveform
(including pauses), unless a peak limit of 0.95 requires a smaller gain.
Silence stays exactly silent. This is amplitude normalization, not perceptual
LUFS normalization. No gating, filtering, emotion features, compression or
semantic analysis is performed. Quantized PCM16 is used for both playback
and the encoder. At 24,000 Hz, each 20 ms frame contains exactly 480 samples
(legacy eSpeak: 22,050 Hz / 441 samples);
the last frame is zero-padded for RMS calculation.

Every frame supplies `min(4 * RMS, 0.8)` model-voltage units to every selected
JO-A/B neuron via the original `FlyBrain.step(inject=...)`. Gain 4 is an
unvalidated engineering calibration; cap 0.8 follows flytalk. Unlike flytalk's
song-dependent 90th-percentile calibration, this gain is fixed across poems.
There is no frequency differentiation or physical sound-pressure unit.
This is an envelope bridge to an anatomically grounded input, not a model of
antennal mechanics, frequency tuning, particle velocity or hearing speech.

## From us: runs and measurements

Each run resets all voltages/spikes and restarts the original PCG64 noise
stream at seed 64. Noise remains active. On the same CPU software/configuration
this is repeatable; cross-device/build bitwise identity is not promised.
Four numba threads are recorded. There is 0.5 s of excluded silent settling,
1 s of measured silent baseline, the complete audio window, then 1 s of
silence. A short baseline may still contain initialization transients.

Every timestep records all fired neuron indices in `spikes.npz` (offsets index
the concatenated events; indices map to `data/brain.npz` body IDs). Global and
monitored-group spike counts are retained at 20 ms; counts for every cell type
at 100 ms and exact phase totals are in `populations.npz`. Rates divide counts
by neuron count and seconds. No membrane-voltage trace is captured in v1.

RESPONSE reports baseline/during/tail mean Hz/neuron, change from baseline,
the largest absolute global departure during audio and its timestamp,
rankings by absolute population change and by mean activity, and group sizes.
No statistical significance is inferred from a single run. Small populations
can dominate per-neuron rankings; both size and rate are displayed.

The global display uses a causal five-step (100 ms) moving mean. A descriptive
baseline band is ±max(3 baseline smoothed SD, 0.02 Hz/neuron). A state transition
is recorded after 60 ms continuously in a new above/within/below-band state.
These are threshold crossings, not discovered neural states. Recovery is the
first 200 ms continuously inside the band after the padded audio window;
null means recovery was not observed within the one-second tail, not infinite
persistence. Baseline deviations alone do not establish sound causation.
The validation script additionally compares same-seed silence and pulse runs.

Monitored groups include input JONs, their actual direct postsynaptic partners
(excluding input neurons), descending-neuron superclass, upstream WING_MN
types, and available DNa02, DNp01, DNg100, MDN, pIP10 and dPR1 types. A graph
neighbor is called a structural target, not a physiologically verified auditory
pathway. Missing groups are reported as unavailable. Upstream associates
DNa02 with steering, DNp01 with giant-fiber escape, DNg100 with forward walking,
MDN with backward walking, and pIP10 with song command. We report their names
and activity without inferring executed behavior. Arbitrary upstream game
labels such as punch/kick are excluded. No affect/valence categories are used.

## From us: interpretation

`interpretation.py` accepts a strict response-summary schema, rejecting extra
fields. It has no poem argument or network access. An explicit allowlist
extracts duration, baseline changes, peak timing/line number, changing cell
types, transition count, tail deviation and recovery. The exact input is saved
as `reading-input.json` and under `reading.input_summary`. Cell names come only
from the verified connectome annotations. Rules turn these measurements into
a restrained short reading. Metaphors about emphasis, release and closure
belong to READING, not RESPONSE. An LLM provider is not included in v1.

Full result JSON contains a separate display-only poem/line-timing field for
replay. The interpreter is never passed that result object. Artifacts stay
locally in `results/<run-id>/`; the submitted poem and synthesized voice are
saved there, unencrypted. The local API has no external service dependency
after installation. Bind to loopback only; this prototype has no user accounts.

## Current limits

English voice only; at most 2,000 characters, 80 lines and 60 seconds of audio.
Only one run at a time. No live animal, validated speech-hearing model, learned
mapping, experimental affect classification, multi-seed inference or physical
motor simulation. The 20 ms timestep caps firing at 50 Hz and discards fine
acoustic structure. Upstream LIF/sensory-feedback limitations remain intact.
The timing of a reading depends on voice, line splitting, normalization, frame
size, gain, neural model, baseline and threshold choices; all are inspectable.

## From us: the visible fly

The listening scene uses a static NeuroMechFly anatomical surface derived
from a female micro-CT specimen, separate from the male connectome. A speaker
and acoustic rings stage the encounter. Rings encode audio RMS; antennal
color encodes recorded JON firing. No pose, locomotion, wing movement or
comprehension is inferred from the activity. See [the exact visualization
mappings and asset provenance](docs/VISUALIZATION.md). This layer receives
completed records; it has no route back into the simulator or interpreter.

## Matched silence benchmark (schema 1.1)

Each new reading now runs twice: the poem's RMS injections, then zero injections
for exactly the same number of timesteps. Both use the same `reset(seed)`, frozen
weights, warmup, initial baseline and tail. In pinned `brain.py`, every step draws
an `(n, batch)` noise array regardless of activity; resetting the seed therefore
reproduces the random input stream. We verify identical pre-stimulus spike counts
and matching configuration, seed, populations and weights before comparison.
The control has ongoing tonic/noise/connectome activity: silence is not zero firing.

`benchmark.json` contains control provenance, the global control trace, paired
poem-minus-silence rates, the largest absolute paired population differences and
monitored pathways. Phase means use raw counts; displayed traces and peak use a
causal 100 ms average. The original initial-baseline measurements remain separately
available in `response`. The interpreter now receives only a strict controlled
summary, never the poem. Its prose explicitly identifies one paired seed.

This is a counterfactual within this computational model. One pair is not a
normative baseline, a significance test, or evidence of language processing.
Multiple paired seeds and non-speech acoustic controls remain necessary to assess
robustness and specificity. Matching noise controls stochastic input; subsequent
network trajectories are allowed to diverge. Small cell types can dominate rankings.
Full poem and silence spikes and population counts are downloadable independently.

## Spatial spike display

The listening chamber stages the existing NeuroMechFly body facing an illustrative
speaker. Its pose remains static; rings encode audio RMS and antennal color encodes
recorded JON activity. The separate neural volume uses finite `positions` from the
pinned MaleCNS `brain.npz`: 140,638 of 166,700 neurons have coordinates. We choose
12,000 uniformly spaced valid neuron indices, independent of activity, and light a
point only when its recorded neuron fired in that 100 ms bin. The index list,
coordinates and firing-bin membership are saved in `neural-display.json`. Camera
orientation and lighting are presentation choices. Points are neither full neuron
morphologies nor an anatomical registration to the separate female body. No edges,
brain regions, body movements or behavioral meanings are invented for this display.

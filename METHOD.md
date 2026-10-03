# The Drosophila Critic — public encounter method

The fly receives sound-derived input. No poem text, transcription, word
meaning, embedding or language model enters its simulation. This is a
computational artwork and listening experiment, not evidence of poetry
comprehension or a reconstruction of subjective experience.

**RESPONSE** means measurements of simulated activity. **READING** means an
interpretation of those measurements. The current main page uses plain
measurement explanations; the older literary reading layer remains in the
repository for local research, outside the public app. Its response-only
boundary remains intact.

## From MaleCNS and fly.ai

The distributed MaleCNS v1.0 network contains 166,700 neurons and 25,582,938
directed connections. Identities, annotations and coordinates come from the
data. Synapse signs inferred from neurotransmitter predictions, postsynaptic
normalization, LIF dynamics and stochastic noise are fly.ai modeling choices.

The pinned source is [fly.ai at 5e931b8](https://github.com/alextitonis/fly.ai/tree/5e931b8dc4856550565c5fa129d3d0c055af3dd1).
We retain the original weights, 20 ms timestep, tau 100 ms, gain 3, tonic 0.14,
noise amplitude 0.22, noise probability 0.024 per neuron per step, threshold 1,
reset 0 and no refractory period. Incoming sensory synapses are retained.
Weights are checked before/after runs. The browser stores original Float32
weights losslessly and reproduces the original CPU accumulation and rounding
order; PCG64 fixtures establish exact numerical agreement on the tested host.

The original `flytalk.ear_cells` function selects all 138 JO-A/B cells, both
sides. The [entry-point audit](docs/AUDITORY_ENTRY.md) records the exact types
and the amplitude convention inherited from flytalk. We do not introduce
unmeasured subtype tuning or reinterpret upstream game labels as biology.

## From us: the acoustic bridge

The curated synthetic recording is Kokoro `af_sarah`; the human is Denny
Sayers’s LibriVox performance of Blake’s *The Fly*. Whole-record RMS is 0.05,
including pauses, with linear gain and a 0.95 peak ceiling. No compression is
used. Visitor audio follows the same target and is lowered further if its
crest factor would otherwise cause clipping. The actual gain, input/output
RMS and peak are saved. Different durations remain different total exposures.

The current receiver is the implemented Göpfert & Robert 2002 sound-transfer
fit (394 Hz resonance, Q 1.24, velocity gain 1.13). Waveforms decoded at 48 kHz
are treated as virtual local air-particle motion. RMS 0.1 represents virtual
velocity RMS 0.5 mm/s. The exact interval-held mechanical solver yields modeled
antennal displacement; 20 ms RMS envelopes drive the existing JO-A/B cells.
The fixed 200 Hz reference displacement maps to 0.4 abstract voltage, capped
at 0.8. This conversion is a provisional engineering calibration, not a
measured membrane current or a calibrated loudspeaker-to-fly distance model.

The published equation was reconstructed and its numerical convergence tested.
That is not full physiological validation. Active level-dependent mechanics,
adaptation, spatial direction, receptor nonlinearities and fine auditory
subtype responses remain unsupported. No separate active-force model is
silently combined with this fit. See the [source audit and validation](experiments/receiver-v2/CALIBRATION.md).

## Runs, controls and measurements

Curated performances each have four sound/silence pairs (seeds 1101–1104), with
the same reset, noise stream and duration within each pair. Silence has
spontaneous firing. A seed represents simulator variability, not another fly.
Both half and double receiver strengths remain archived; the public nominal
setting was selected before looking for a dramatic poem difference.

Runs include 0.5 s settling and 1 s baseline before sound, five 20 ms frames of
mechanical decay after sound, then 3 s of neural tail. Playback starts when the
audio starts and continues through that silent tail on one Web Audio clock.
The pre-sound record remains in the JSON. Partial final bins use their actual
duration. The spatial and aggregate playback contract is [documented here](docs/ENCOUNTER-V2.md).

The interface displays raw firing rates for sound and matched silence, plus
mean differences during and after the voice. Groups are the whole network,
injected JO-A/B cells, their direct structural postsynaptic partners excluding
the inputs, descending neurons, and flytalk’s wing motor group. None is an
emotion category. A connection to a hearing neuron is anatomical evidence,
not proof of a specifically auditory function.

Curated traces show four-run means and min/max ranges, not confidence intervals.
A fixed, uniform sample of 12,000 neurons supplies the spatial view. Every
amber point corresponds to an actual recorded spike in its 100 ms bin, at an
actual supplied coordinate, from seed 1101. Counts for named groups use all
members, not just this visual sample. Scales and the sample are shared across
conditions. Visitor results use one sound/silence pair at seed 1101 and are
explicitly exploratory. They receive no replicated-result claim.

## What moves on screen

Reader gestures are stage animation. Antennal amber intensity is a display of
modeled vibration strength; it is not a resolved oscillation, physical motion
prediction or new receptor model. The trace and neural-input trace use separate
scales, common across recordings. Reduced-motion mode disables gestures and
antennal flashes; neural flashes can also be switched off while traces continue.

The articulated flybody anatomy follows recorded MuJoCo trajectories. All
spikes in DNg100, left/right DNa02, DNp01, DLM motor cells and left/right b1/b2
motor cells feed an isolated, versioned adapter. It maps absolute smoothed rates
to commands for the original frozen walking and flight policies. The body can
therefore move during silence. Our gains, minimum gait speed, takeoff/landing
supervisor and arena corrections are engineering choices, described in the
[adapter method](docs/NEURAL-BODY-ADAPTER.md). No overall activity threshold,
poem-quality score or text controls the body.

The body and neural displays show the same designated seed, 1101. Movement
figures average four paired runs for each curated recording; visitor figures
use one pair. Seeking restores saved body and joint transforms on the same
audio clock. Wing blur uses a small set of poses from the published wingbeat
pattern; the renderer does not show slow, invented flapping. Follow view changes
camera framing, not physical dimensions. Reduced-motion mode uses the fixed
arena camera and stable wing exposure.

This is modeled movement influenced by simulated neural activity. Body sensors
feed only the body policies. Motion does not change the imposed sound field or
feed visual/proprioceptive signals into the nervous system. The female anatomy
and MaleCNS male nervous system are separate models. Their coupling has not
been physiologically validated.

## Browser recording and privacy

After deliberate activation, workers load the 138,576,365-byte compressed neural
model and about 17 MB of body-processing assets. Independent sound and silence
workers process the recording locally; each MuJoCo worker is single-threaded. It uses the same
neural arithmetic and receiver as the curated experiment. Model chunks are
checksum-verified before caching. Cancelling terminates every simulation worker; replacing
input cannot reuse old spatial firing as a substitute result.

No audio, transcript or response is uploaded. The page restricts fetches to its
own origin, and the deployed site has no compute endpoint. The original audio,
processed WAV, normalization, injected frames, rates, spatial sample, raw group
counts, seed, body transforms, movement commands, confinement events, and model
hashes can be saved locally. Private results are held
in memory, not cached. Browser codec/resampling, microphone gain and room noise
are uncontrolled; requested microphone processing settings are not guaranteed
by hardware. A silent file is a valid zero-input experiment, not an error.

## Historical scope

Earlier amplitude-only and text-to-TTS results remain unchanged with their own
method snapshots. The [prototype method](docs/PROTOTYPE-METHOD.md) documents
those settings, including its shorter baseline/tail and its separate literary
interpreter. The current page does not silently upgrade or relabel those runs.

## Playback camera

The close camera keeps a fixed viewing direction rather than rotating with the
fly's heading. Its centre follows a Gaussian-smoothed thorax path (60 ms standard
deviation, 180 ms each side), interpolated on the playback clock. The centre
may differ from the recorded thorax by at most 0.12 cm, to retain the animal
inside the close frame during fast turns. This is display stabilization only:
body transforms, commands, audio, neural activity and movement measurements are
unchanged. The same playback time gives the same framing after seeking or at
different rendering rates. Reduced-motion mode retains the fixed wide view.

# Shared encounter and playback contract

The finalization release adapts existing nominal runs into one public scene.
It does not overwrite `encounter-v1`, retune the receiver or regenerate the
scientific evidence to suit the design. The reference, camera/material choices
and original scientific protocol remain in [ENCOUNTER.md](ENCOUNTER.md).

## Experience

Silence, human, robot and visitor are conditions in the same interface. Silence
belongs to the currently selected recording’s length and starting state.
Curated stanza buttons jump to that recording’s own start time and keep playing
to the end. Switching readers starts the corresponding stanza. Visitor audio
has no automatically invented stanza/line alignment.

A single Web Audio clock drives sound, neural bins, antenna envelope, traces
and text. Playback begins at sound time zero and includes the saved post-sound
period. Pausing freezes the view. Reduced motion disables reader gestures and
antenna intensity changes, and defaults neural flashes off. A separate flash
switch preserves audio and measured traces. Mobile controls remain sticky
within the encounter. WebGL failure leaves audio, graphs and numerical tables.

## Versioned static contract

`experiments/encounter-v2/manifest.json` identifies existing audio/spatial sound
records, new silence spatial records, group membership/labels/scales, passage
boundaries and scientific source artifacts. Its referenced `playback-a.json`
and `playback-b.json` use `schema_version: fly-playback-v2`:

- `audio_duration`, `playback_duration`, `start_time`, `bin_seconds` establish
  clocks. Negative time is saved pre-sound activity; playback begins at zero.
- `activity.sound`, `.silence`, `.change` hold mean/minimum/maximum rates in
  spikes/s/cell, in the manifest’s group order, in 100 ms bins. The final partial
  bin uses its actual duration. `.change` is paired subtraction before averaging.
- `summary` holds during-sound raw rates, silence rates, their difference and
  post-sound difference, with repeated-run ranges.
- `input` holds 20 ms waveform RMS, mechanical displacement envelope in model
  nm and actual injected model voltage. Last acoustic frames are zero-padded.
- `seeds`, `normalization`, and `body.available` identify provenance/limits.
  No body trajectory is currently available.

Silence spatial files are rebuilt from their own actual spike archives. They
use exactly the same 12,000 neuron indices and coordinates as sound playback.
A firing bin is a deduplicated union of sampled cells firing in its interval;
it is not their firing rate or an invented interpolated frame.

`static/neural-capture.js` records the same kind of output during visitor runs.
It has no model-update or RNG access. `static/playback-data.js` maps its named
groups into the common contract; a single run has coincident min/mean/max,
never a fabricated confidence band. The whole-network/group summaries count
all neurons, independent of the visual sample.

The manifest's acoustic scales cover the maxima of both examples. Visitor input
can enlarge those scales for every condition together; switching readers never
rescales one recording to look stronger. Neural rate scales remain common too.

## Visitor lifecycle

Only an explicit processing click loads connectivity. The draft contains the
original blob, decoded mono samples, duration and hash. Preview is separate
from the result. Two worker runs compute sound and equal-duration silence at
seed 1101; neither a robot reference run nor upload is required. Processing
normalizes linearly to target RMS 0.05, lowered if necessary to avoid clipping,
then rounds to the same PCM16 convention as Python. Silence remains valid.

`local-listening-v2` exports model and original-weight hashes, receiver matrices,
normalization, source duration, injected input, raw group/global counts, sampled
spikes, seed and common playback metrics. Original/processed WAV can be saved
separately. Visitor export has no semantic interpretation input or public link.

Cancellation increments a generation, aborts fetching, terminates the worker,
and rejects pending work. Late worker events cannot replace a newer result.
Microphone tracks stop on completion/cancel/error/page exit. A failed cache
checksum removes that corrupt entry; errors do not select recorded responses.

## Measurements and interpretation

Primary copy explains a named population’s measured change against silence.
The repeated-run sentence checks whether all paired mean differences share a
sign; it is not a significance test. The archived numeric-only literary
interpreter remains separate and is not used to decorate the new page.

Model/spatial downloads and all rates are inspectable. The broader theoretical
argument belongs to the research archive. See [METHOD](../METHOD.md) for
scientific boundaries and [BODY-CONTROLLER](BODY-CONTROLLER.md) for the motion
investigation and its measured outcome.

# The Drosophila Critic

**A fruit fly listens to poetry.**

A Synthetic Humanities Lab project. A working critical instrument:

```
poem → fixed synthetic voice → PCM audio → RMS envelope → JO-A/B input
     → full frozen flybrain connectome → recorded spikes → RESPONSE → READING
```

The fly receives sound-derived input, never a semantic representation of the
poem. RESPONSE describes simulated neural activity. READING interprets only
those measurements, without access to the poem text.

## Share and collaborate

- **[Play the Blake edition](https://synthetic-humanities-lab.github.io/drosophila-critic/)** — William Blake's *The Fly*, with its actual recorded neural response. This static edition is explicitly labeled; it does not accept new poems.
- **[Lab repository](https://github.com/Synthetic-Humanities-Lab/drosophila-critic)** — source, method, public artifacts, issues and pull requests.
- **[Host the full simulator](docs/DEPLOYMENT.md)** — the Docker deployment supports new poems; a hosting account is still needed.

The opening poem is [William Blake's *The Fly*](https://poets.org/poem/fly),
from *Songs of Experience* (1794), in the public domain. Its title/author and
text are display/TTS material only; none reaches the interpreter.

## Run this installed copy

From this directory:

```sh
./run.sh
```

Open **http://127.0.0.1:8765/** in Chrome, read the prefilled Blake poem or paste
another poem, and select **READ TO FLY**. After computation, press the audio play
button. A 3D NeuroMechFly specimen faces a speaker while the current poem
line, acoustic rings, antennal activity annotation and neural traces replay together.
The body has a static pose; it does not perform inferred behavior. RESPONSE and READING appear after the silent tail;
they can also be inspected immediately with the measurements button.

The custom Web Audio player is verified in Chrome and the Codex embedded
browser, including completion of synchronized replay. It replaces the native
media controls that crashed the embedded browser in the first version.

No API keys, remote TTS, browser speech voices, LLMs or Node build are
required. Three.js and the anatomical GLB are supplied as local static assets. One FastAPI process serves static HTML/CSS/JS and
runs a single simulation worker. Do not launch multiple server workers: the
single-run admission guard is process-local.

## Fresh setup

Tested on macOS arm64 with Python 3.12.14. Use Python 3.12 and Git. The pinned
NumPy/SciPy and eSpeak loader need compatible binary wheels for your platform;
other platforms have not been tested. Initial package/connectome downloads
require the internet; readings run entirely locally afterward.

```sh
mkdir -p vendor data results
git clone https://github.com/alextitonis/fly.ai.git vendor/fly.ai
git -C vendor/fly.ai checkout --detach 5e931b8dc4856550565c5fa129d3d0c055af3dd1
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c 'from flybrain import download; download("data")'
.venv/bin/python -m critic.simulation
.venv/bin/python scripts/setup_voice.py
./run.sh
```

The upstream files total approximately 260 MB; the runtime plus stored spike
records requires additional disk space. The simulator itself is unchanged.
`vendor/`, `.venv/`, `data/` and `results/` are excluded from Git. The source pin
and result hashes identify the code/data used. Checksum failures stop a run.

The fixed Kokoro voice adds about 354 MB of model/voice assets. Blake’s
*The Fly* produces approximately 26.17 seconds of audio. First use also loads
the connectome and compiles numba. Timing is machine dependent. UI progress
reports real pipeline stages and simulation steps.

## Boundaries and modules

| Module | Accepts → produces |
| --- | --- |
| `critic/neural_tts.py` / `tts.py` | Text → fixed Kokoro PCM (legacy eSpeak provider retained), exact line intervals, voice provenance |
| `critic/audio_encoder.py` | PCM only → normalized PCM and per-frame RMS/JON voltage |
| `critic/simulation.py` | Acoustic frames only → original FlyBrain spikes and population counts |
| `critic/response.py` | Recorded counts and numeric line intervals → measurements and timeline |
| `critic/interpretation.py` | Strict response-only schema → rule/template reading |
| `critic/pipeline.py` | Orchestration, separate display text, saved audit artifacts |
| `critic/server.py` | Local/hosted API, job progress, bounded public storage, artifact serving |
| `static/` | Accessible controls, SVG traces, replay and evidence disclosure |

TTS is a small provider protocol. The default is Kokoro v1.0, fixed `af_sarah`
voice, speed 1.0, native pitch, synthesis seed 64, CPU execution. Model/voice
hashes and runtime settings are recorded. No silent fallback is permitted.
The waveform is normalized to whole-record
RMS 0.1 with a 0.95 peak ceiling. Every 20 ms, `min(4 × RMS, 0.8)` is injected
equally into the **138 neurons** returned by upstream `flytalk.ear_cells`.
No frequencies, phonemes, words or emotion labels are mapped to neurons.

The original MaleCNS network contains **166,700 neurons and 25,582,938
connections**. Every reading resets to seed 64, settles silently for 0.5 s,
measures a 1 s baseline, runs the full audio, then records 1 s of silence.
The original stochastic LIF model remains active and weights remain unchanged.

RESPONSE includes baseline/during/tail rates, signed baseline deviations,
largest absolute global departure/time, sustained band-crossing events,
observed/censored recovery, changing and active annotated cell types, direct
JON postsynaptic targets, descending neurons, wing motor neurons and named
output types. All population rates are normalized by population size.

READING is entirely rule-based. `ResponseSummary` rejects unexpected fields;
`summarize_response` explicitly selects measurements and numeric line labels.
The interpreter has no poem argument or provider/network calls. No optional
LLM integration is included in v1; any future one must accept exactly the same
response-only object.

## Validation

```sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/validate.py
.venv/bin/ruff check critic tests scripts
.venv/bin/ruff format --check critic tests scripts
node --test tests/audio-player.test.mjs
```

Unit/API tests cover silence preservation, frame boundaries/padding, exact
playback/encoder PCM agreement, capped amplitude mapping, deterministic TTS,
changed-poem → changed-audio → changed-injection behavior, interpretation
allowlisting, input limits, cross-origin rejection and busy-run handling.

`scripts/validate.py` runs the actual full connectome on silence, a rectangular
amplitude pulse, a repeat with the same seed, and William Blake's
[*The Fly*](https://poets.org/poem/fly) (public
domain). It checks downstream propagation, exact reset repeatability, frozen
weights and reconciliation of reported rates with raw spikes. Evidence is
written to `docs/validation.json`, with full artifacts under `results/`.

Reopen that saved poem after validation:
http://127.0.0.1:8765/?reading=blake-the-fly

## Inspect a result

Each successful run has its own `results/<uuid>/` directory and replay URL.

- `result.json`: response, timeline, interpretation, configuration and hashes;
  the poem is in a **separate display-only field**.
- `audio.wav`: normalized voice actually supplied to the encoder.
- `encoding.json`: every frame's sample bounds, RMS and injected voltage.
- `reading-input.json`: the exact text-free interpretation input.
- `spikes.npz`: all fired neuron indices concatenated, timestep offsets, dt;
  map indices to body IDs with `data/brain.npz["ids"]`.
- `populations.npz`: all cell types' 100 ms counts, exact phase totals,
  monitored groups' 20 ms counts and global counts.
- `population_metrics.json`: baseline/during/tail rates for every annotated type.
- `tts.npz`, `tts.json`: original synthesis PCM and voice/line metadata.
- `METHOD.md`: the method snapshot for that run.

JSON has strict finite numbers; missing recovery is `null`. UI downloads are
restricted to completed-run artifacts. Failed runs produce an explicit error,
never a neural fallback. Artifacts persist across restarts; in-flight jobs do
not resume. Poems/audio are saved unencrypted on this computer and may sync
through the enclosing OneDrive folder. Local runs bind to loopback; public
containers use the explicit host and temporary-storage settings in
[DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Scientific seams and next work

Read [METHOD.md](METHOD.md), the pre-implementation
[auditory audit](docs/AUDITORY_ENTRY.md), and the exact
[population inventory](docs/population-inventory.json).

The envelope gain is an engineering choice, not biological calibration.
There is no model of frequency tuning, antennal resonance, adaptation or
particle velocity. The 20 ms LIF timestep is coarse; speech carrier frequency
is discarded. The voice is deliberately synthetic and line-wise synthesis
imposes prosody. A one-second baseline/tail and one seed support descriptive
measurements only. Small populations and spontaneous drift may dominate
baseline-relative rankings. Global averaging can conceal local effects.

The most useful next steps are matched-duration silence controls for every
poem, multiple seeds and longer settling/tail windows; anatomical/literature
review of downstream auditory populations; then an independently validated
acoustic transducer. The smoother Kokoro voice replaces eSpeak through its provider boundary;
it changes the experimental instrument, so results preserve voice provenance. Improve interpretation only after these measurement limits are
clear. No claim of comprehension, emotion or executed behavior follows here.

## Upstream acknowledgments

fly.ai/flybrain is MIT-licensed (retained at `vendor/fly.ai/LICENSE`). MaleCNS
data provenance and transformation code are retained upstream. eSpeak NG is
third-party GPL-licensed software installed through `espeakng-loader`, not
copied into this source tree; retain its notices if packaging/distributing it.

## Listening-scene revision

Saved opening poem: http://127.0.0.1:8765/?reading=blake-the-fly

The left panel contains a lit 3D fly facing a speaker, an oblique/dorsal camera
switch, the current verse and play/pause/seek controls. The right panel shows
recorded global activity, the acoustic envelope and changing cell types.
RESPONSE and READING remain separate below.

NeuroMechFly anatomy is Apache-2.0; licenses, source commit and hashes are
bundled with the GLB. Its female micro-CT surface is not registered to MaleCNS.
See [visualization provenance](docs/VISUALIZATION.md). Rebuilding the asset is
optional and uses `requirements-assets.txt`; no physics engine is installed.
Kokoro weights are Apache-2.0; kokoro-onnx is MIT. See
[the model wrapper](https://github.com/thewh1teagle/kokoro-onnx).

### Silence benchmark and spatial replay
New readings include a full-duration zero-input run with the same seed and reset.
The main trace overlays matched silence; population rankings and the text-blind
reading use poem-minus-silence differences. The initial baseline metrics are still
saved separately. This doubles simulation work. One paired seed establishes a
model counterfactual, not a statistically typical response. Additional seeds and
non-speech controls are the next experimental step.

The listening chamber displays the fly anatomy, spoken line, injected envelope,
and a spatial view of real recorded spikes at supplied MaleCNS coordinates.
`neural-display.json` documents its fixed 12,000-neuron sample. Full poem and silence
spikes remain available for audit; body motion is not simulated.


### Comparing performances and critical lenses
The public recorded edition now offers the fixed Kokoro reference and a human
performance by Denny Sayers (LibriVox, 2006). Selecting a performance swaps its
waveform, response, matched silence and interpretation together. Circuit and
affect-theory lenses read the same response-only summary. Neither receives the
poem text. This is a deliberate extension of the original single-voice protocol.

The human recording is public domain in the USA. `examples/sayers-source.json`
records its source, checksum, excerpt bounds and approximate display-only line
timing. To reproduce its simulation, install the optional media decoder with
`.venv/bin/python -m pip install av==18.1.0`, then run
`PYTHONPATH=. .venv/bin/python scripts/import_sayers.py`.
The importer preserves pacing, normalizes through the same encoder, and runs a
separate equal-duration silent control. Whisper was used once for editorial
alignment, not in the auditory or simulation pipeline; it is not a runtime dependency.

See [Critical directions](docs/CRITICAL-DIRECTIONS.md) for the affect-theory,
digital-humanities and posthumanities research agenda and its limits.

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

## Delivery comparison bench (phase one)

Open **Delivery bench** from the listening chamber, or visit
`https://synthetic-humanities-lab.github.io/drosophila-critic/comparison.html`.
This is a separate, newly level-matched ensemble experiment; the chamber's original
single-seed records remain labeled as such.

The committed `experiments/delivery-v1/PROTOCOL.md` specifies the stimuli and primary
measurements. `RESULTS.md` reports outcomes and limitations. The bench uses the
unchanged `SimulationRunner` and original fly.ai `FlyBrain`. There is no learned
readout or change to the neural model. Eight matched seeds, seven conditions and two
silence durations give 72 actual simulations. Exact repeat and polarity controls
are independently simulated and checked against complete spike arrays.

After the normal environment/connectome setup:

```sh
PYTHONPATH=. .venv/bin/python scripts/delivery_bench.py --pilot
PYTHONPATH=. .venv/bin/python scripts/delivery_bench.py
PYTHONPATH=. .venv/bin/python scripts/delivery_bench.py --analyze
.venv/bin/python scripts/export_replay.py
.venv/bin/python -m http.server 8766 --directory dist
```

The second command resumes matching cached runs and completes the chosen seed set;
it refuses cached input mismatches. The third recalculates analysis without
simulation. Pilot runs took approximately 8–14 seconds each on the development
machine; all 72 simulations totaled 707 seconds excluding setup and final analysis.
Raw spikes and population files occupy about 2.1 GB under `results/delivery-v1/` and
are not committed. Public artifacts include the source and processed WAVs, every
injection, per-seed scalar responses, mean/range timelines, full global/group counts,
all cell-type phase counts, provenance and a hash manifest for the local raw archive.
The public comparison is recorded replay, not an online simulation service.

`counts.npz` keys are `<condition>_<seed>_global_counts`, `..._group_counts`,
`..._phase_counts`, `..._type_sizes`. Silence keys begin `silence_<audio-frame-count>`.
`group_names` and `type_names` identify axes. Global/group counts use 20 ms steps:
25 warmup + 50 baseline + the manifest's audio frame count + 50 tail steps.
Cell-type phase counts have rows baseline/audio/tail. Counts are spikes, not rates.

Focused checks: `python -m pytest tests/test_delivery.py tests/test_interface.py` and
`node --test tests/*.test.mjs`. No additional runtime dependency is required.

## Temporal confirmation (phase two)

Open `temporal.html` from the chamber or comparison bench. This separate experiment
uses eight new seeds (101–108), the same neural model and five seconds of aftermath.
The protocol was written before running. It confirms temporal measurements separately
from exploratory episode selection and supplies a text-free summary to an affect
interpreter. The page distinguishes response, functional implication and interpretation.

```sh
PYTHONPATH=. .venv/bin/python scripts/temporal_confirmation.py
PYTHONPATH=. .venv/bin/python scripts/temporal_confirmation.py --analyze
.venv/bin/python scripts/export_replay.py
.venv/bin/python -m http.server 8766 --directory dist
```

The first command performs/resumes 64 simulations (six stimuli plus two duration-matched
silence controls per seed). It requires the v1 stimulus artifacts already committed
under `experiments/delivery-v1`. The second analyzes saved runs without resimulation.
Raw spikes remain under `results/temporal-v2`; public evidence is under
`experiments/temporal-v2`. See its `PROTOCOL.md` and `RESULTS.md`.
`counts.npz` follows the v1 key/axis conventions but includes **250 tail steps**.
Use each condition encoding's frame count for the audio phase. The default chamber
and v1 observation remain one second; only this experiment requests a five-second tail.

The reverse-frame stimulus is an encoder-only control, not an oral performance.
Its frame clocks refer to injection slots; RMS/drive are reversed from the reference,
and remaining sample metadata is inherited slot metadata, not a synthesized waveform.
The localized-pause WAV preserves the reference PCM samples exactly, relocating 180 ms
of digital silence. It is not renormalized or compressed.

## Matched-history probe experiment (phase three)

Open `history.html` from the chamber or temporal report. This tests whether two
different earlier inputs change reception of an identical later passage beyond
activity that would continue without it. The four conditions are A/B history ×
passage/quiet, repeated at 0, 0.5 and 2 second gaps with eight new seeds. Eight
independent duplicate runs give **104 simulations** in total. The protocol was
committed before simulations in `experiments/history-v3/PROTOCOL.md`.

```sh
PYTHONPATH=. .venv/bin/python scripts/history_experiment.py
PYTHONPATH=. .venv/bin/python scripts/history_experiment.py --analyze
.venv/bin/python scripts/export_replay.py
.venv/bin/python -m http.server 8766 --directory dist
```

The first command resumes only matching cached conditions; the second verifies
raw artifacts and recalculates the report without resimulation. It requires the
normal fly.ai/connectome setup and the committed v1 reference PCM. No new model
or dependency is required. Raw spikes remain in `results/history-v3`; exact WAVs,
encodings, provenance and compact counts are public under `experiments/history-v3`.

Count archive keys are `<condition>_<seed>_group_counts`, `..._global_counts`,
`..._phase_counts`, `..._type_sizes`. Axes are `group_names` and `type_names`.
Global/group counts are spikes at 20 ms steps: 25 warmup + 50 baseline + the
manifest's stimulus frame count + 50 tail. Phase rows are baseline/audio/tail.
The probe slot starts at `75 + round(probe_start / 0.02)` and lasts 100 steps.
Public response JSON contains all five factorial contrasts, groups, gaps,
fixed windows, per-seed 100 ms traces and exact-control results.

## Controlled emphasis in the listening chamber (phase four)

The main page now includes **Compare controlled emphasis** (direct link: `?mode=emphasis`).
Select earlier/later emphasis or either against unchanged audio, then switch the heard
recording at the same paused timestamp. Line highlighting, frame RMS/JON drive and
silence-subtracted ensemble traces follow the selected audio clock. This is separate
from the earlier single-seed original-performance replay. Both use the tested AudioContext
transport, and changing modes pauses the other player.

```sh
PYTHONPATH=. .venv/bin/python scripts/emphasis_experiment.py
PYTHONPATH=. .venv/bin/python scripts/emphasis_experiment.py --analyze
.venv/bin/python scripts/export_replay.py
.venv/bin/python -m http.server 8766 --directory dist
```

32 simulations: unchanged, earlier emphasis, later emphasis and equal-duration silence,
using seeds 301–308. Source-line intervals 2 and 17 receive complementary smooth power
gains; energy added to one is removed from the other, avoiding global renormalization.
No off-target sample changes. The exact gain envelopes, PCM and injected input are saved.
This is amplitude emphasis only; naturalness has not had independent human listening review.

Artifacts are in `experiments/emphasis-v4`; raw spikes remain locally in
`results/emphasis-v4`. The protocol was committed before running. Count archive layout
matches v3, with 75 pre-audio steps, 1309 audio steps and 50 tail steps. See `RESULTS.md`
for local versus whole-audio outcomes. The interpreter uses a separate strict numerical
schema and receives no text. No new dependency or model mechanism was added.

### Corresponding performance passages

Open `/?mode=passages` for stanza-by-stanza listening to the two level-matched recordings, native-time neural traces, actual injected input, and three external amplitude-following baselines. Switching recordings goes to the same stanza's start and pauses playback. The interpreter sees only numerical summaries; approximate human alignment and baseline limitations are displayed.

Rebuild this retrospective analysis without running new simulations:

```sh
PYTHONPATH=. .venv/bin/python scripts/passage_comparison.py
.venv/bin/python scripts/export_replay.py
```

The committed v1/v2 count archives supply the measured original-fly responses. Calibration uses v1 synthetic seeds 64–71; evaluation uses v2 seeds 101–108. See `experiments/passages-v5/RESULTS.md` for the actual findings and the distinction between local differences and what simple input tracking explains.

### Annotated population follow-up

The stanza interface includes a five-candidate held-out population comparison. Discovery uses v1 seeds 64–71; fixed-candidate validation uses v2 seeds 101–108. No new fly runs or training occur. All selected candidates, including failures, and all 350 discovery comparisons are public under `experiments/populations-v6`.

To reproduce, local raw `results/delivery-v1` and `results/temporal-v2` population archives plus the pinned connectome files are required:

```sh
PYTHONPATH=. .venv/bin/python scripts/population_screen.py discover
PYTHONPATH=. .venv/bin/python scripts/population_screen.py validate
.venv/bin/python scripts/export_replay.py
```

The committed compact count archives also let tests reconstruct the held-out comparisons without downloading the connectome or rerunning simulations. Read the protocol before interpreting the gates: validation reuses the same performances, and residual differences only challenge three simple amplitude approximations.

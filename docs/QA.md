# Verification record — 2026-09-20

Environment: macOS arm64, Python 3.12.14, pinned requirements, four numba
threads, unmodified upstream commit 5e931b8dc4856550565c5fa129d3d0c055af3dd1.

- 18 unit/API tests passed. Two deprecation warnings originate in the
  Starlette/httpx/anyio test-client compatibility layer; no test failed.
- Ruff lint and formatting checks passed. Python compilation and JavaScript
  syntax checks passed. No separate static type checker is configured.
- Full-connectome validation passed; see `validation.json`. Same-seed reset
  reproduced counts exactly, raw spikes reconciled with reported counts,
  weights remained unchanged, and pulse input changed 121 frames of direct
  JON postsynaptic activity compared with matched silence.
- Rossetti's complete eight-line poem ran through the actual TTS, transducer,
  166,700-neuron simulator, analyzer and response-only interpreter.
- Submitted the example through the browser UI and observed genuine loading,
  simulation progress, completed replay and artifact availability.
- Chrome: native audio playback progressed, line labels and neural readouts
  updated, the silent tail replayed, and RESPONSE/READING appeared afterward.
- Inspected initial, replay and measurement layouts with browser screenshots.
  At 390 × 844, both page and content widths were 390 px (no horizontal page
  overflow); charts, tables and controls remained accessible. Restored normal
  viewport afterward.
- Fixed a discovered live-list ordering bug: population traces now follow
  response ranking, including replay of earlier files.
- Codex embedded browser: initial and completed layouts rendered correctly,
  but native audio playback crashed the embedded page twice. Chrome playback
  succeeded. This browser-specific limitation is documented in the README.

These checks establish software behavior and evidence boundaries, not
biological validation of the speech encoder or literary authority of its
interpretation. The baseline-relative poem response is a single seeded run.

## 2026-09-20 — neural voice and anatomical listening scene

- Canonical voice changed to fixed local Kokoro `af_sarah`, speed 1.0, TTS
  seed 64, CPU ONNX. Model and voice bank hashes are verified before use.
  Repeated synthesis produces identical normalized frames on this host;
  different text produces different actual acoustic input. Legacy eSpeak
  artifacts and provider remain explicit, never silently substituted.
- 19 Python tests passed, including the new neural voice boundary test;
  2 Node player tests passed (clock/pause/resume/seek/end and cancellation
  during initialization). Ruff check/format and JS syntax checks passed.
  Two upstream FastAPI/Starlette deprecation warnings remain.
- The complete fixed-seed neural-voice Rossetti run produced 12.448 s of
  audio and 748 neural frames (including baseline/warmup/tail). Raw spikes
  reconcile with every reported count, weights stayed frozen and the
  interpretation input excludes poem text. Evidence:
  `docs/validation-neural-voice.json`, `results/validation-kokoro/`.
- Browser QA: anatomical GLB loads, speaker is visible, dorsal/oblique
  camera is available, current verse and actual neural/acoustic traces
  update during playback. Pause freezes the displayed trajectory.
- Custom Web Audio playback completes in Chrome and the Codex in-app
  browser. This fixes the previous embedded-browser native-audio crash.
- At 390 × 844, document scroll width equals viewport width (390 px);
  scene, verse and controls fit, with response below on narrow screens.
- No anatomical motor simulation was added. The fixed pose uses upstream
  anatomy/neutral-pose data; acoustic rings and JON color are display-only.
  The female surface / male connectome distinction is explicit in METHOD.

- A fresh in-app-browser submission (`1bee66ae-328b-4be1-85fc-3686b781cbc4`)
  completed and matched the canonical saved audio SHA256 and every neural
  timeline frame exactly. In-app browser console contained no errors/warnings.
  Manual seeking to 4.12 s aligned line 3, JON input 0.433 and global rate
  3.868 Hz/neuron. Oblique/dorsal switching was visually inspected.

## Blake / lab publication

The default poem is William Blake’s *The Fly* (1794), using the Academy of
American Poets text with all five stanzas preserved. The full-connectome
reading is 26.1653 seconds with 1,434 frames including warmup/baseline/tail.
Raw spike totals reconcile with every timeline count; the interpreter’s
input excludes poem text. 22 Python tests and two player tests pass.

The static publication uses only this designated public-domain reading,
with an explicit recorded-edition notice and no poem-submission control.
The downloadable JSON, WAV, injections and spike/population artifacts are
from the actual completed run. New-poem hosting is a separate Python
container deployment; no paid hosting was provisioned.

## Listening chamber and paired silence — 2026-09-20

- Full Blake waveform was replayed through the frozen model at seed 64; its 1,434
  global spike counts exactly reproduced the previously published poem record.
- A second full-duration zero-input run used the same reset, seed and parameters.
  Pre-stimulus counts matched exactly. Mean whole-network activity was 3.884326
  with the poem and 3.872880 with silence (difference +0.011446 Hz/neuron).
  Direct JON partners differed by +0.638534 Hz/neuron. Peak smoothed global
  separation was -0.329394 at 9.28 s. These are single-pair measurements.
- Sampled spatial firing bins were reconciled directly against raw spike indices.
- A fresh two-line Blake run completed the full TTS → poem simulation → silence
  simulation → controlled reading pipeline (2.536 s of audio, 252 total steps).
- 27 Python tests and 2 audio lifecycle tests passed; Ruff lint/format passed.
- Chrome playback verified changing line, injected voltage, JON rate, point-cloud
  firing and playback clock. Desktop and 390 px mobile layouts inspected; mobile
  camera framing adjusted to preserve the fly and speaker at narrow aspect ratios.

## Two performances and affect lens — 2026-09-20

- Imported the poem-only 32.30–77.40 s excerpt of Denny Sayers's LibriVox source,
  checksum `8eb6b0d8c43d298b34f137cbbed9e06a007c39fef235183f7b3aa682fcc4889b`.
- Ran all 166,700 neurons for that 45.10 s waveform and its same-seed silent control.
  Global paired difference +0.0009485 Hz/neuron; downstream JON partners +0.245777
  approximately. Audio hash, trajectory, duration and interpretation differ from
  the synthetic reference while the poem identity remains the same.
- Actual RMS differs despite the shared peak-limited normalization rule; the UI
  exposes 0.052 for the human performance and 0.094 for the synthetic reference.
- Browser verified human selection updates duration, audio URL, neural readouts,
  benchmark and reading; playback advances line highlighting and measured activity.
  Affect lens selection exposes the correct performance's 29.82 s peak and source
  links. Approximate imported line timings remain marked for human listening review.

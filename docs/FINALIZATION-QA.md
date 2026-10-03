# Finalization verification — 2 October 2026

This record distinguishes automated checks, browser observations and unverified
hardware/platform paths. Publication verification is recorded below.
The accepted brief is [FINALIZATION-GOAL.md](FINALIZATION-GOAL.md).

## Data and numerical checks

- Existing frozen-connectome runs are retained. The v2 exporter adapts them and
  builds silence displays from their own spike archives; no scientific weights,
  seeds, receiver calibration or poem outcomes were changed for this interface.
- Browser/Python comparison passes all 100 full-network voltage/spike steps with
  supplied noise, and again with the browser generating PCG64 noise itself.
- Both complete poems match Python in **every global count, named-population
  count and sampled firing bin**. See `experiments/browser-v2/capture-parity.json`.
- Browser silence, a gated 200 Hz tone, and an identical repeat produce genuine
  records. Silence is active; the pulse changes downstream firing; the repeat
  reproduces all response hashes exactly. This does not validate fly hearing.
- One capture benchmark took 39.84/62.70 seconds for 26.17/45.10 seconds of sound.
  Another with competing QA pages took 57.75/94.43 seconds. Both are retained;
  a further repeat took 57.66/93.43 seconds. An exact PCG64 hot-loop optimization
  and skipped empty capture memberships brought the final run to **46.38/40.37
  seconds**, passing both twice-spoken-duration targets. All response hashes
  stayed identical. One million NumPy samples/final states per supported seed
  pass too. Device load and scheduling still matter. Transfer is 138,576,365 bytes.
  Fixed arrays are a lower bound of 208,664,308 bytes, not measured peak memory.
- Tested browser: Codex IAB Chromium 154 on the development Mac (14 reported
  hardware threads; 32 GB reported device memory). No other browser engine or
  actual mobile hardware is qualified for local simulation.

## Actual browser journeys

- Complete human and robot playback reaches 0:48 and 0:29, including the silent
  post-sound period. It does not stop at a stanza boundary or four seconds.
- A human stanza-three start at about 0:17 switches to the corresponding robot
  stanza at 0:10.74. Audio is not stretched. Pause, replay, seek-to-end and deep
  links were exercised. The scrubber resetting its value before seeking was
  found during QA and fixed.
- Human-length silence selects its own recorded spikes and 0:48 clock. Its
  changing sample count is not a frozen sound display or baseline-subtracted zero.
- Neural flashes can be switched off while traces remain. The close-view control
  enlarges the anatomical fly; its antenna colour represents the mechanical
  envelope, not resolved oscillations or inferred movement.
- The public robot example was fetched, decoded, previewed and processed locally
  into a new visitor result; both sound and silence completed. Its newly recorded
  neural activity replays in the shared scene through the full 0:29 clock.
- Cancellation during local processing returned controls and preserved the draft.
  Restart completed. Unit tests additionally cover termination, rejected pending
  work, failed initialization, stale responses and a late microphone stop event.
- A 390 × 844 iframe exercised the real responsive layout, including sticky
  reachable transport controls. This is a layout test, not mobile hardware.
- A local-only failure harness disabled WebGL, selected reduced motion, simulated
  refused microphone access, and failed the human response fetch once. Audio and
  numerical traces worked without 3D; refusal gave a file alternative; selecting
  the human again recovered. No harness is included in the deployed build.

## Privacy and remaining test limits

The clean local release's server log recorded 21 curated-playback requests and
zero connectivity, worker or API requests. Only deliberate local processing
loads model chunks. The page restricts fetches to its own origin. Source review
found no audio/result upload, telemetry or external processing endpoint. File
names are rendered as text, not HTML. Private recordings/results are kept in
memory; only versioned model assets use Cache Storage.

The actual file-picker test remains unverified: the user explicitly allowed
`experiments/encounter-v1/b.wav` at localhost, but browser automatic permission
review still rejected the action. The public-example path exercises decoding,
simulation and replay; it does not establish that OS file selection works.
No workaround was used. Actual microphone capture was not exercised with room
hardware; the denial fixture and lifecycle unit tests are not a microphone test.

PCM16 WAV export is checked at the byte/header/sample level. The browser tool's
download event has not yet confirmed an exported file, so OS download handling
remains a manual check. Invalid/overlong/non-finite input is covered by focused
unit tests. Browser decoder allocation can occur before duration validation;
unusually long compressed files remain a memory risk despite the 64 MB file cap.

## Body-controller outcome

The published flybody walking checkpoint passed standing, forward, turning and
exact-repeat command tests in an isolated Python environment. No physiological
neural-to-controller conversion was qualified. Body motion is therefore absent
from both example and visitor replay, explicitly documented in
[BODY-CONTROLLER.md](BODY-CONTROLLER.md). Small poem-induced differences in the
candidate motor outputs were recorded without magnification or a movement score.

## Release checks and deployment

Checks passed: `ruff check critic scripts tests`, `ruff format --check critic
scripts tests`, **145 Python tests**, and **31 JavaScript tests**. Python reports
two existing FastAPI/Starlette/anyio deprecation warnings. Static export succeeds.

### Published verification

Functional commit: `95dd76c483a50679200c8e8b139351c9ed826566`.
Interface module: `encounter.0182f4235edf0d89.js`.
[Pages deployment](https://github.com/Synthetic-Humanities-Lab/drosophila-critic/actions/runs/37092990425)
and [CI/container check](https://github.com/Synthetic-Humanities-Lab/drosophila-critic/actions/runs/37092990420)
both succeeded. CI also reports upstream Node-action and runner deprecation
notices; these did not fail the build.

The live index, interface module, playback/model manifests, asset notice,
archive and recording redirect match the clean local export byte for byte.
Checksums are in `experiments/browser-v2/deployed-assets.json`.

At the public URL, human playback reached 0:48/0:48 and robot playback reached
0:29/0:29 with the completion state. Robot-length silence played its own neural
record. The public-example draft then completed both local worker runs on the
deployed site, entered YOUR VOICE with newly captured spikes, and replayed to
0:29/0:29. Its share button was hidden and its single-run qualification visible.
The measured direct-partner rates were 2.3975 during sound and 2.1253 during
silence, a +0.2722 spikes/s/cell difference. No console error/warning appeared.

The actual deployed page was also inspected in a 390 × 844 iframe. Body width
and scroll width were both 390 pixels; playback controls remained in the
viewport. Its human recording and neural display played. This remains a
responsive-layout observation, not a phone simulation benchmark.

Screenshots are retained locally in `output/qa/finalization/`; the public
README includes the deployed encounter. Neither failure harness nor private
recording files were committed or published.

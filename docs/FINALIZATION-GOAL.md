# The Drosophila Critic — public app finalization goal

Status: executed release brief, 2 October 2026. Implemented outcomes, the body
controller's limit and remaining platform checks are in `GOAL-STATUS.md`.

## Objective

Finish as much of the public Drosophila Critic app as can be responsibly shipped
in one sustained implementation run. Deliver and verify a polished encounter on
the existing Synthetic Humanities Lab GitHub Pages site, rather than another
experiment dashboard or planning document.

The invitation is **Can you move a fly with your rendition of The Fly?** Visitors
can watch the human and robot examples, compare either with silence, and record
or select their own reading. After local processing, their recording plays in
the same scene with its own measured response. Reactions unfold with the audio.
There is no forced stillness, delayed verdict, drum roll, winner, or poem score.

Make substantial, reviewable progress even if the body-controller integration
encounters a scientific or browser-runtime limit. Complete the shared encounter,
visitor flow, silence comparison, explanation, accessibility, and release QA
independently of that integration. Do not mark unsupported body movement done.

Repository: `/Users/starkdj/Library/CloudStorage/OneDrive-Personal/Documents/drosophila-critic`

Public site: https://synthetic-humanities-lab.github.io/drosophila-critic/

## Accepted decisions and authority

- The user accepts an existing research body controller, including one previously
  trained to reproduce real fly movement. This revises the earlier prohibition
  against learned controllers for this specific purpose. Keep that controller
  fixed; do not train it on poem responses or desired entertainment outcomes.
- Preserve the frozen connectome and established receiver. No poem text,
  transcription, embeddings, semantic analysis, or LLM enters neural or movement
  processing. Displaying Blake's text is separate from processing audio.
- A controller does not establish that its coupling to this connectome is valid.
  Test and disclose that connection. Neither general firing nor audio volume is
  an acceptable substitute for a supported movement command.
- Silence is the control. Human, robot, and visitor are listening conditions;
  the robot is not a biological standard or a target to beat.
- Use the existing recordings and their credits. Keep one displayed poem.
- Reactions appear during playback, including any supported body movement. Keep
  the measured post-sound period available without imposing a separate reveal.
- Use plain explanatory copy. Preserve RESPONSE as measurement and READING as
  an explicitly separate inference wherever those labels remain. Remove the
  generic literary interpretation from the principal experience. No hosted LLM.
- Implement, test, commit only the task's changes, publish through the existing
  repository/deployment, and inspect the deployed site. No paid services,
  accounts, submission backend, researcher outreach, or unrelated collection.
- Follow applicable repository instructions. Preserve historical results,
  archive links, unrelated changes, and user files, including `Fly videos/`.

## Starting point: inspect, reuse, then change

The current app already has curated recordings, a Three.js scene, measured
spatial samples, a literature-informed receiver, and a full-connectome browser
worker. Visitor processing is on `listen.html`, with a separate trace-only
result. The worker currently returns only a small set of population counts;
visitor spatial playback will need real sampled spike output and coordinates.

Read `docs/GOAL-STATUS.md`, `docs/ENCOUNTER.md`, `docs/BROWSER-BENCHMARK.md`,
`static/encounter*`, `static/local-listening.js`, the worker and audio modules,
the result exporter, and relevant tests. Recheck current source and artifacts;
this brief is not evidence that a feature still works. The README currently
mixes current public behavior and superseded local-prototype behavior.

Record a short implementation checklist and current screenshots. Make the
smallest coherent changes to the existing architecture; avoid a framework
migration or a new general-purpose simulation platform.

## Workstream 1: one finished encounter

### Visual composition

- Retain the reference's recognizable fly, oblique physical scene, concrete
  materials, contact shadows, and black neural display with amber activity.
  Revisit the recorded reference in `docs/ENCOUNTER.md` and available user
  reference files before revising the composition. Respect asset licenses.
- Make the fly and nervous system the visual focus. Reduce the reader figures'
  dominance. Make both brain and ventral nerve cord legible without scrolling
  away from playback controls. Keep a useful vertical composition on mobile.
- Add a close view of the antennae driven by modeled mechanical output if the
  anatomical asset and data support it. Disclose magnification or slowing. A
  20 ms envelope must not be presented as a resolved biological vibration trace.
- Reader gestures remain stage animation. Fly-body motion, antennal mechanics,
  and neural flashes each have their own documented source; do not blend them
  into an apparently biological animation without a data contract.
- Keep the scene restrained: no random neural firing, decorative network lines,
  arbitrary camera shake, body jitter, or sound-volume-driven flight.

### Playback and comparisons

- Offer clearly named SILENCE, HUMAN, ROBOT, and YOUR VOICE entry points. Visitors
  can immediately play an example or start their own recording; no compulsory
  tutorial or model download precedes curated playback.
- Use the silence run belonging to the selected recording's duration, initial
  state, and configuration. Identify which recording's silence is being shown;
  do not imply that one short silence clip controls every recording.
- Present both ordinary activity and change relative to silence intelligibly.
  Silence has spontaneous activity; a baseline-subtracted zero is not a silent
  nervous system. Keep visual scales and sampled neuron selection consistent.
- Preserve complete audio playback, play/pause, seek, replay, five curated
  stanza navigation points, and shareable example/stanza links. A stanza is a
  starting point, not an automatic stop. Switching readers uses each recording's
  own clock, without time stretching.
- Audio, antenna display, spikes, body trajectory, traces, and highlighted text
  use one playback clock. Specify treatment of warmup and the silent tail.
- Explain what the visitor sees beside the relevant display, for example:
  "Each flash marks a simulated nerve cell firing" and "Some cells fire even
  when there is no sound." Values, groups, time intervals, and uncertainty must
  come from data, not from these illustrative sentences.
- Keep comparison details and research downloads accessible but secondary.
  Explain repeatability in ordinary language and avoid jargon in primary copy.

## Workstream 2: visitor recording is a first-class experience

- Integrate microphone and file selection into the encounter. Let visitors
  audition, replace, and deliberately submit their local recording for
  processing. Show duration, the 60-second limit, recording state, and errors.
  Here, submitting means starting local processing, not uploading to a server.
- Explain and request the model download before fetching it; retain versioned
  caching, progress, cancellation, and the instant curated-playback alternative.
- Decode and validate audio, preserve pauses and internal dynamics, and document
  the level policy. Do not silently compare differently normalized datasets.
  Equal RMS is not equal exposure; durations remain visible. Preserve original
  audio, processing metadata, and the actual injected signal for local export.
- Make the primary result the visitor's sound versus its own equal-duration
  silence run. Avoid rerunning a robot comparison as a compulsory processing
  cost when it is not needed. Reuse a reference only when every relevant input,
  level, numerical configuration, and checksum matches; never relabel old data.
- Add bounded, deterministic spatial sampling to visitor simulation output as
  needed. Show actual recorded spikes at actual neuron coordinates in the same
  scene. Never use the curated spatial animation as a visitor-result fallback.
- Maintain a versioned playback/result contract for curated and visitor data,
  including condition, clocks, audio, baseline, populations, spatial sampling,
  mechanical output, optional body trajectory, configuration, and provenance.
- Do not invent line alignment for arbitrary recordings. Use elapsed time for
  visitor playback unless the visitor supplies explicit timing; no automatic
  transcription is required. Curated passages keep their existing timings.
- Handle cancellation and replacement without stale worker events, old audio,
  incorrect overlays, or retained microphone access. Release tracks, workers,
  object URLs, and large buffers when appropriate.
- Keep audio/results on the device; cache model assets rather than private
  recordings. Make local result/evidence export useful. Do not create a public
  share link that falsely promises access to a private local recording.
- Clearly label visitor results as a single simulation comparison. Do not give
  them the curated four-run repeatability claim. Maintain an honest device
  support boundary and graceful fallback to recorded examples.

## Workstream 3: a defensible moving body

Resolve feasibility early, without allowing it to consume the entire release.
Audit one suitable research controller and implement the smallest justified
connection if the checks below pass. Do not launch a broad controller search
or keep changing assumptions until a poem causes dramatic motion.

Research starting points:

- https://github.com/TuragaLab/flybody
- https://www.nature.com/articles/s41586-025-09029-4
- https://github.com/NeLy-EPFL/flygym
- https://github.com/alextitonis/fly.ai/blob/main/world/README.md

1. Inspect the actual controller, license, checkpoints, command interface,
   dependencies, body assets, and runtime. Distinguish the current full-connectome
   model from upstream constructed networks, altered weights, and scripted
   wandering. Check browser deployment cost before committing to integration.
2. Specify the neural-to-body mapping before judging poem outcomes. Identify
   the neurons, evidence for their motor role, temporal filtering, units,
   controller inputs, and every engineering assumption. If a low-level controller
   replaces the role of nerve-cord circuitry, disclose which recorded neural
   outputs actually control it. Running the entire network does not mean every
   part of it causally controls the body.
3. First verify the body controller follows its documented commands. Then test
   a justified motor-pathway positive control, silence, repeatability, and the
   existing auditory inputs. A stationary fly is not evidence of a poem's failure
   if the proposed neural-to-body connection fails its positive control.
4. Test whether poem-induced changes reach the selected motor-related outputs
   and change the body relative to silence. Retain spontaneous baseline movement
   if the model produces it. Never use a threshold on total firing as a reward.
5. Keep one-way neural drive distinct from a closed brain/body feedback loop.
   Do not invent feedback into the frozen model or claim embodied validation
   merely because a physics engine moves a body. Keep existing neural numerical
   equivalence tests intact.
6. Qualify local visitor execution as well as curated replay: runtime, memory,
   cancellation, deterministic replay, unsupported devices, and additional
   downloads. A Python-only controller or prerecorded trajectory does not make
   arbitrary visitor body reactions available in the browser.

Record the decision and evidence in `docs/BODY-CONTROLLER.md`. If the connection
is defensible and feasible, ship body reactions synchronized to both curated
and newly processed visitor audio, with recorded provenance and a concise
method explanation. State that the body coupling is a model, not physiological
validation of reactions to speech.

If only curated body replay is feasible, distinguish that capability plainly
and keep visitor neural replay complete. If the mapping or controller checks
fail, ship the improved neural/antenna encounter with no fabricated walking or
flight. Keep "Can you move a fly?" framed as the research question; do not promise
literal behavioral results the shipped mode cannot provide. Report the precise
blocker and the smallest next experiment, rather than calling motion complete.

## Workstream 4: copy, method, and release coherence

- Rewrite all primary copy for an interested visitor without neuroscience
  vocabulary. Explain the picture and controls before interpreting results.
  Remove generic affect-theory paragraphs, repeated caveats, robot-as-standard
  language, and statements about pleasure, fear, understanding, or poem quality.
- Keep the intellectual argument for the separate essay/research archive. The
  public encounter can be playful without making unsupported biological claims.
- Provide a compact METHOD with the sound-to-neural pipeline, simulated versus
  measured biology, provisional coupling, body-controller assumptions if used,
  neural sample versus aggregate trace, normalization, recording credits,
  licenses, privacy, and evidence downloads.
- Rewrite README around the current public app, optional local simulation,
  exact build/test/run commands, and verified limitations. Label historical
  architecture as historical; preserve the underlying records and links.
- Update the encounter manifest, release status, and QA record. Give new
  scientific/configuration artifacts new versions; never overwrite old runs.

## Verification and acceptance

Use the existing Python/JavaScript test patterns; add focused tests for changed
data and control boundaries, rather than tests that merely repeat UI markup.
Run relevant checks, then the repository's release checks:

```sh
.venv/bin/ruff check critic scripts tests
.venv/bin/ruff format --check critic scripts tests
.venv/bin/python -m pytest -q
node --test tests/*.test.mjs
.venv/bin/python scripts/export_replay.py
```

Preserve the browser/Python numerical fixtures. Run the full equivalence and
performance checks again if neural arithmetic, sampling overhead, worker
execution, or controller integration could affect their guarantees. Record
commands, outcomes, hardware/browser, and checks that could not be exercised.

Inspect the actual app at desktop and mobile widths, locally and after public
deployment. Capture reviewable screenshots and a short interaction record if
available. At minimum, verify:

- Both complete curated recordings play beyond four seconds and reach their
  actual end. Stanza switching, seeking, pause/resume, replay, and deep links
  retain correct audio and synchronized data.
- Silence shows its own real neural trajectory and correct associated condition.
  The example page does not download connectivity or call a compute service.
- An audio file travels end to end through local processing into the shared
  scene. Silence, a diagnostic tone/pulse, and a poem produce the actual
  corresponding input and response, including any supported body trajectory.
- Microphone permission, capture, preview, and processing work where hardware
  access is available. A file-upload test alone is not a microphone test.
- Invalid/oversized/silent audio, refused microphone permission, failed assets,
  interrupted downloads, processing cancellation, replacement recordings,
  unavailable WebGL, and unsupported devices have useful recoverable states.
- Worker sampling and rendering do not invent, misattribute, or retain spikes
  across condition switches. Numerical summaries reconcile with saved runs.
- Keyboard navigation, visible focus, labels, contrast, reduced motion, and a
  useful non-3D view work. The poem appears once; controls remain reachable.
- Privacy checks confirm no visitor audio or result leaves the browser. Model
  asset fetches and explicit user-initiated downloads are distinguishable.
- Published assets, method links, archive/deep links, credits, browser model
  checksums, and the deployed release version resolve correctly.

## Execution, check-ins, and completion

Start by inspecting current state, then implement. Do not stop at another plan.
Continue through ordinary reversible fixes and established publication steps.
Use short progress updates during active work. At major milestones, report a
concrete result or show a screenshot: shared encounter working, visitor replay
working, body-controller decision, and deployed verification. These are progress
check-ins, not approval gates.

Ask the user asynchronously only when a choice materially changes the agreed
experience, scientific claims, privacy, cost, or model boundaries. Keep working
on independent tasks while awaiting an answer. Silence is not permission for
such a change. Do not repeatedly ask about choices settled in this brief.

Maintain `docs/GOAL-STATUS.md` as an honest implementation record. Do not stop
after receiver research, a visual mockup, passing unit tests, or a local build.
Finish the authorized app work and inspect the recipient-facing site. If an
external block prevents publication, preserve a runnable, reviewed local build
and report exactly what remains.

Final handoff: live URL, what visitors can now do, screenshots, implemented
movement capability and its limits, verification performed, any remaining
defects or unsupported devices, and the single most important next task. Keep
the summary plain and distinguish shipped behavior from research prototypes.

The goal is complete only when the independent app deliverables are shipped and
verified, the body-controller investigation has a documented evidence-based
outcome, and no required work remains unaccounted for. A failed controller test
can close that investigation; lack of time alone cannot.

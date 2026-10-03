# Release status — published and verified, 2 October 2026

Execution brief: [FINALIZATION-GOAL.md](FINALIZATION-GOAL.md). The independent
app deliverables are published on the [Synthetic Humanities Lab site](https://synthetic-humanities-lab.github.io/drosophila-critic/).
The body-controller investigation has a documented no-motion outcome. Platform
QA limits remain explicit in [FINALIZATION-QA.md](FINALIZATION-QA.md).

- [x] Versioned common playback contract, actual silence spikes, shared scales,
  input/mechanical traces, raw activity and differences against silence.
- [x] One encounter with human, robot, silence and local visitor replay; larger
  fly/nervous-system views; one poem; complete audio and stanza navigation.
- [x] Integrated recording/file controls, preview, deliberate local processing,
  download disclosure, caching, progress, cancellation and private exports.
- [x] Actual worker spatial capture matches saved Python poem runs exactly.
- [x] Research controller command tests and explicit no-motion release decision.
- [x] Desktop/responsive-layout, fallback, error recovery and focused regression
  checks. Actual file-picker, microphone hardware and OS download limitations
  are recorded rather than reported as passes.
- [x] Current README/method and preserved prototype documentation/history.
- [x] 145 Python tests, 31 JavaScript tests, lint/format checks, successful CI
  and Pages publication. Deployed audio, local processing, responsive layout
  and exact build/asset identity verified.

## Scope of the result

The receiver, original weights, timestep and noise remain unchanged. New
`encounter-v2` artifacts adapt existing nominal runs; no outcome was retuned.
The public robot example completes local sound/silence processing and replays
newly computed neural activity in the same scene. Visitor trials are single
comparisons; curated traces show four-run means and ranges. Neither is a poem
score or a claim about feelings.

The optional flybody research controller passed stand/forward/turn/repeat tests.
The candidate movement outputs do not yet supply a qualified control signal.
No body animation was substituted. [BODY-CONTROLLER.md](BODY-CONTROLLER.md)
identifies the missing neural-to-command calibration and browser qualification.

Browser timings vary with other active work; all measurements are retained in
`experiments/browser-v2`. The optimized release passes both full-poem timing
targets with unchanged numerical results. Curated playback has no model download. Desktop visitor
processing requires an explicit 139 MB model download; phones remain playback-only.

## Retained evidence

- `experiments/encounter-v1`: original mechanical-receiver performances, four
  seeds, half/nominal/double strengths and original auditory result protocol.
- `experiments/encounter-v2`: shared sound/silence display contract and input scales.
- `experiments/browser-v1`: original numerical/performance qualification.
- `experiments/browser-v2`: current capture, numerical parity and diagnostic checks.
- `experiments/body-controller-v1`: pretrained-policy command tests and measured
  candidate motor-output audit.
- Earlier amplitude, temporal, emphasis, passage and receiver experiments remain
  linked through the research archive with their original qualifications.

The next movement experiment would qualify one lateralized steering adapter,
starting with a motor-pathway positive control and silence before testing poems.
It is research work, not a hidden animation parameter.

Functional release: `95dd76c483a50679200c8e8b139351c9ed826566`.
Published interface version: `0182f4235edf0d89`. The remaining documentation
closeout does not change that interface or its scientific artifacts.

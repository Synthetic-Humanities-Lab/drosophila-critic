# Moving listening arena — implementation status

The moving-arena release is implemented, published, and browser-verified on
3 October 2026. This supersedes the stationary-body scope of the previous release.

Accepted scope: walking, turning, takeoff, flight, and landing; a bounded
listening arena; a disclosed neural-to-command adapter; movement during
silence; genuine body replay for curated and visitor recordings; local visitor
processing within five minutes for 60 seconds of audio on a tested desktop.

## Required evidence

- [x] Published walking and flight controllers reproduced locally.
- [x] Continuous, actuator-driven transitions demonstrated and recorded.
- [x] Motor adapter fixed using controls, with causality/repeatability tests.
- [x] Four paired seeds for both curated performances and silence.
- [x] Articulated arena, follow/overview cameras, locator, and neural display.
- [x] Browser policies/observations checked against original SavedModels.
- [x] Visitor body simulation, cancellation, runtime/memory measurement.
- [x] Playback/seek, desktop/mobile, accessibility, missing-asset checks.
- [x] Existing neural/receiver/privacy regression checks.
- [x] Published site inspected, with before/after captures.

No prerecorded visitor substitution, no semantic analysis, no trained readout,
and no changes to the frozen connectome or auditory receiver are authorized.
An unresolved controller or runtime requirement must remain marked unfinished.

Evidence, numerical tolerances, hardware limits and actual captures are in
[MOVING-ARENA-QA.md](MOVING-ARENA-QA.md).

## Deployment

Implementation commit: `12d28fbf21c688f7ad47dfed70ac706bf7274078`.
[Successful GitHub Pages deployment](https://github.com/Synthetic-Humanities-Lab/drosophila-critic/actions/runs/37108456240).

The live site was checked through full human, robot and silence playback,
corresponding stanza switches, saved-pose seeking, reduced motion, and the
controller-proof page. A fresh visitor processing run of the public robot
example finished in 137.38 seconds, including its own silence and both body
trajectories, then replayed fully to 29.28 seconds.
[Visitor evidence](../experiments/body-controller-v2/deployed-visitor.json).
The curated page's observed assets included no connectivity, policy weights or
physics runtime: [resource inventory](../experiments/body-controller-v2/deployed-replay-assets.json).

The runtime acceptance measurements apply to the tested desktop. Phone processing,
other desktop/browser qualification, and browser-wide peak memory measurement
remain outside the demonstrated coverage. The body coupling remains an explicit
engineering model, not physiological validation.

One additional live-site file-picker retest (the public human WAV) was blocked
by browser approval review reporting declined permission. No workaround was
attempted. The deployed built-in robot-example visitor flow passed separately.

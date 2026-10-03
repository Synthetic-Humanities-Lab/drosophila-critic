# Moving listening arena — implementation status

Implementation and local checks are complete. Public deployment verification is
the remaining release step. This supersedes the stationary-body scope of the
previous finalization release.

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
- [ ] Published site inspected, with before/after captures.

No prerecorded visitor substitution, no semantic analysis, no trained readout,
and no changes to the frozen connectome or auditory receiver are authorized.
An unresolved controller or runtime requirement must remain marked unfinished.

Evidence, numerical tolerances, hardware limits and actual captures are in
[MOVING-ARENA-QA.md](MOVING-ARENA-QA.md).

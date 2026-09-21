# Local emphasis v4 — results

32 full frozen-connectome simulations completed, seeds 301–308, four conditions. Protocol commit `f583fd2` predates the runs. No connectome, dynamics or encoder parameters changed.

## Finding

Earlier versus later emphasis produces a downstream contrast meeting the declared temporal criterion in the first target window. The second target reverses direction in all eight runs but does not meet the full criterion: its mean temporal RMS is slightly below pointwise seed variability. Both findings are retained. This separates directional agreement in window averages from the stricter temporal test.

Neither edited version versus the unchanged recording meets the criterion at either target. All those downstream window averages nevertheless have the expected same sign in eight of eight seeds. No descending window meets the criterion in any comparison. These are descriptive outcomes, not statistical significance or evidence of bodily action.

| Comparison | Window (s) | Mean Δ Hz/neuron | Seed signs + / − / 0 | Temporal RMS | Variability RMS | Half cosine | Criterion |
|---|---|---:|---|---:|---:|---:|---|
| earlier_reference | 1.16–2.66 | +0.07284 | 8 / 0 / 0 | 0.12416 | 0.21032 | 0.55336 | Not met |
| earlier_reference | 17.58–19.08 | -0.08219 | 0 / 8 / 0 | 0.12306 | 0.23960 | 0.52398 | Not met |
| later_reference | 1.16–2.66 | -0.06981 | 0 / 8 / 0 | 0.14337 | 0.19685 | 0.50980 | Not met |
| later_reference | 17.58–19.08 | +0.07645 | 8 / 0 / 0 | 0.12486 | 0.22447 | 0.32566 | Not met |
| earlier_later | 1.16–2.66 | +0.14266 | 8 / 0 / 0 | 0.22395 | 0.20671 | 0.78840 | Met |
| earlier_later | 17.58–19.08 | -0.15864 | 0 / 8 / 0 | 0.21701 | 0.22579 | 0.93493 | Not met |

## Local versus overall response

| Comparison | Whole-audio mean Δ | Off-target mean Δ |
|---|---:|---:|
| earlier_reference | +0.001160 | +0.002240 |
| later_reference | +0.003460 | +0.003437 |
| earlier_later | -0.002300 | -0.001197 |

The stronger first-window contrast coexists with a small whole-recording average difference. This is a measured relocation of response, not a score for a better performance. A receiver following present amplitude can explain it; no history dependence or emotional category follows.

## Acoustic checks

The edits transfer energy between fixed intervals without rescaling the rest of the recording. Every off-target PCM sample is unchanged. All versions have the same duration and timing, RMS within 1e-6 quantization tolerance, peaks below 0.95 and zero capped injection frames. Smooth 80 ms gain ramps avoid abrupt gain jumps. No independent human listening review of naturalness has occurred; these remain amplitude diagnostics rather than new expressive performances.

| Condition | PCM RMS | Peak | Integrated injected drive |
|---|---:|---:|---:|
| reference | 0.049998488 | 0.503754 | 3.767851409 |
| earlier | 0.049998488 | 0.503754 | 3.756752631 |
| later | 0.049998487 | 0.503754 | 3.757418320 |
| silence | 0.000000000 | 0.000000 | 0.000000000 |

Equal waveform energy does not guarantee identical integrated input. The two emphasis conditions differ in integrated drive by approximately 0.018%; this difference is recorded rather than silently treated as zero. Their difference from the reference is also retained.

## Interpretation and audit

The rule-based reading receives only strict numerical window summaries and times, never the poem or waveform. It describes local recruitment where the criterion is met and preserves non-detections. The main interface now couples the exact audio, shared line timing, actual injection, silence-subtracted ensemble trace and response-only reading. Switching audio keeps the timestamp and pauses playback; modes cannot play simultaneously. The earlier single-seed chamber remains distinctly labeled.

Raw spikes and population files remain in `results/emphasis-v4`; public count archives, source/PCM/input hashes, exact gain envelopes, protocol and result JSON permit reconstruction. Initial pre-target trajectories match. All simulations preserve the same model configuration and frozen weights. Tests reconstruct both primary windows from saved integer spike counts.

Simulation runtime: 389.8 seconds for 32 runs, excluding loading and analysis.

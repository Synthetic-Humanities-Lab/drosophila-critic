# Local processing: saved silence and completed readings

This release removes repeated work. It does not change the connectome, auditory
receiver, seeded noise, neural timestep, body model, controller policies,
movement adapter, physics timestep or visual sampling.

## Reusable silence

The visitor calculation has always used seed 1101 and a fixed initial state.
Its zero-input run is consequently deterministic and independent of the future
length of the recording. We generate 3,230 steps (64.6 seconds): enough for a
60-second recording, 1.5-second initial baseline, 0.1-second receiver decay and
three-second post-sound interval. A shorter visitor recording uses the exact
prefix that the previous fresh simulation would have produced.

`scripts/build_silence_control.mjs` uses the production `BrowserBrain`, captured
spikes, original weights and PCG64, followed by the production adapter,
supervisor, frozen policies and official MuJoCo WebAssembly runtime. It runs no
audio or interpretation model. The published artifact is generated from that
actual simulation, not from a drawing or approximate movement curve.

The prefix includes:

- global and annotated-population counts at every 20 ms;
- displayed spike identities at every 20 ms, used to reconstruct 100 ms bins,
  including the final partial bin without including future spikes;
- all body positions, orientations, commands, movement states and inversion
  flags, with transition events cut to the interval;
- movement measurements recomputed for the exact end of the visitor's audio.
  A total measured over the longest control is never reused for a shorter one.

Thirteen losslessly compressed five-second chunks total **16,397,000 bytes**;
the app downloads only the required prefix chunks and caches them. Poses remain
JSON double-precision numbers. Neither weights nor poses are quantized.
Checksums cover each compressed chunk. A contract binds the control to neural
configuration/array hashes, populations, display neurons, receiver, initial
random state, body-asset manifest and engine version. CI separately checks
implementation-source hashes and the contract against the current files.

If the control is missing, corrupt, too short or from a different configuration,
the app announces that it is calculating silence locally and records the reason
in the result. Cancellation aborts downloads and terminates active workers.
The saved-control path uses one neural worker and releases its connectivity
before starting the body worker. Curated playback never loads the control or
the processing models.

Result JSON adds `silence_control` provenance, a contract hash,
`processing.saved_control_seconds` and `processing.silence_reused`.
The existing `neural_pair_seconds` and `body_pair_seconds` fields remain for
readers of older exports; they now measure work actually performed, which may
be sound only. Precomputed-control `seconds`/`wall_seconds` are null; original
generation timings are recorded separately. This is still one seed and one
sound/silence comparison, not an additional biological replicate.

## Where the body time goes

A sampling CPU profile of the full 64.6-second silence trajectory on the
available Mac (Node 26, official single-threaded MuJoCo WASM) attributed:

| Work | Sampled seconds | Approximate share |
| --- | ---: | ---: |
| MuJoCo physics | 208.876 | 94.7% |
| Compiled policy matrix products | 6.391 | 2.9% |
| JavaScript | 4.925 | 2.2% |
| Garbage collection | 0.155 | 0.07% |

These are profiler sample estimates, not independent component stopwatch
measurements. The full body run took 220.390 seconds while profiling. The result
does not support an allocation rewrite as a substantial performance fix.
Accordingly, this release retains the current validated physics and controller
implementation. Reducing physics steps would change the numerical model and
requires a separate convergence/behavior investigation.

## Safari comparison

The public 26.165-second robot recording was processed through the actual
recording panel in Safari 26.5, iPhone 17 / iOS 26.5 Simulator, on the available
Mac. The saved-control and fresh-control trials ran successively; no other
full simulation was deliberately run alongside them.

| Stage | Saved silence | Fresh silence |
| --- | ---: | ---: |
| Control load/check | 0.686 s | — |
| Neural calculation | 29.787 s | 59.605 s |
| Body calculation | 98.292 s | 294.361 s |
| Total processing | **130.258 s** | **355.128 s** |
| Loading the completed result from IndexedDB | 0.119 s | 0.094 s |

Global/population counts, sampled spikes, body positions/orientations and all
displayed measurements matched exactly between those Safari runs. The total
was 63.3% shorter in this single comparison. Do not treat that as a guaranteed
phone speedup: the identical sound body's own calculation also varied from
97.793 to 142.691 seconds. The architectural saving is eliminating one neural
and one body calculation, roughly half the serial work. These tests use cached
models/local asset delivery and do not measure a first internet download or
physical-phone thermals/memory pressure.

Evidence: [saved](../experiments/performance-v1/safari-saved-control.json),
[fresh](../experiments/performance-v1/safari-fresh-control.json),
[exact comparison](../experiments/performance-v1/comparison.json),
[CPU profile summary](../experiments/performance-v1/body-profile.json).

## Completed readings on this device

IndexedDB keeps one completed recording, its original audio blob, processed PCM,
response evidence and body trajectories. Reopening restores those exact values
without loading processing workers. It does not recalculate an older result
with a newer model. Its original model/provenance remains in its response file.

Saving replaces the previous entry and its small metadata record in a single
transaction. The landing page reads only metadata until the visitor clicks
**Reopen saved reading**. **Delete saved copy** removes the local entry; it does
not clear unrelated site data or files the visitor downloaded. An interrupted
save preserves the previous committed reading. Unavailable/full storage is
reported without losing the current replay or download controls. Browser
eviction/private browsing can remove local storage; downloads remain the way to
keep an independent copy. Nothing is uploaded.

## Reproduce and verify

```sh
node scripts/build_silence_control.mjs --output output/silence-regeneration --profile
node --test tests/*.test.mjs
.venv/bin/python -m pytest -q
.venv/bin/python scripts/export_replay.py
```

Generation needs the committed lossless browser model and body assets. An
output outside `static/` retains uncompressed neural/body references and the
optional CPU profile for local inspection. Default output is the public
`static/assets/silence-v1` directory; uncompressed references are omitted there.
Run generation only after reviewing any simulator changes, then requalify the
control before publishing. Runtime/source fingerprint failures are a reason to
regenerate and compare, not to bypass verification.

The tests cover all five final-bin remainders, exact audio-end measurements,
model mismatch, corrupt/missing control, cancellation, and the fresh fallback.
The 1,539-step prefix for the public robot recording reproduces the previously
recorded Safari global counts, population counts, displayed spikes, body
positions and orientations exactly. Cross-engine derived angular totals have
a tolerance of 1e-12 revolutions (the observed Node/Safari difference was
3e-15); this is arithmetic rounding, not a changed trajectory.

The maximum-duration check also passed in iOS Safari: a 60-second zero waveform
produced all 3,230 steps, with exactly matching neural counts, displayed spikes,
body positions/orientations and movement metrics against the saved control.
That check overlapped a desktop interface playtest and is numerical coverage,
not a mobile performance qualification. Its result was saved and loaded intact.
Native IndexedDB checks verified round-trip audio/typed arrays, replacement,
rollback when a save is interrupted, and deletion. Storage-quota failure leaves
the current replay and downloads available with an explanatory message.

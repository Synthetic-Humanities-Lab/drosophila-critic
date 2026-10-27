# Body calculation: unchanged-state reuse

This revision keeps the original neural simulation, auditory receiver, neural-to-body
adapter, frozen walking and flight networks, joint geometry, solver, and 50 µs
physics timestep. It changes how the existing calculations are executed. Visitor
recordings still stay on the device.

## What is reused

`BodyRuntime.step` ends each controller interval with `mj_forward`, which evaluates
the new body state for the next controller observation. Before the next interval's
first physics step, the runtime changes controls and timestep only. It does not
change positions, velocities, activations, geometry, or applied forces. A normal
`mj_step` immediately repeats the position and velocity calculations for that
same state.

The narrow `body-stepping.js` adapter remembers the completed forward pass. If
model, data, timestep and Euler integrator still match, it uses the upstream
`mj_step2` operation for the **first substep only**. That operation still computes
actuation, accelerations, constraints, acceleration sensors and integration. All
later substeps call the original `mj_step`. Collisions and kinematics for each new
body state are still calculated. Only duplicate work on an unchanged state is
reused; the number of integration steps and controller updates does not change.

The initial forward pass is special: the XML starts with a 0.2 ms timestep and
the runtime switches to 0.05 ms before its first step. Reusing that pass was the
reason earlier experiments diverged. The adapter now checks the timestep and
forces a full first step. It also invalidates after each use, a different model
or data object, a different integrator, and a failed forward call.

`scripts/body_step.cc` adds one small native binding to the otherwise unchanged
MuJoCo source. It runs the upstream position/velocity checks and recomputes the
forward pass after any numerical position/velocity warning, including an old
warning. It compensates for `mj_step2`'s step-counter decrement, which normally
pairs with `mj_step1`. Physical integration counts therefore remain correct.
This is not a general-purpose cache: a source hash test pins the audited
`BodyRuntime` mutation boundary. Changes to that runtime require reviewing the
reuse assumption rather than merely updating the hash.

## Engine build

The engine still uses MuJoCo commit
`9ecbb9d7b5ee623f54745638d36799ff90e6f7cd` and Emscripten 4.0.10, strict SIMD,
`-O3`, `-ffp-contract=off`, single-threaded execution, and the existing assertions
and exceptions. The final build uses full link-time optimization (`-flto`).
CMake's automatic ThinLTO is explicitly disabled so it cannot override this
setting. Fast math and relaxed SIMD remain off; floating-point precision and
arithmetic order are not relaxed.

The physics binary is 4,672,599 bytes, versus 4,632,279 bytes in the previous
release (about 40 KB larger). It downloads once on demand and is cached under a
new URL; model and policy data keep their existing cache keys. Curated playback
does not download this engine. The worker verifies the binary checksum and
records its version, compiler flags, source and binding hashes, plus the
stepping adapter version in new results.

## Timing method and rejected candidates

Short Node probes favored aggressive compiler inlining. That setting also
increased the engine to 7 MB. Full Safari trials did not establish a corresponding
benefit, and it was not adopted. A first version of the adapter wrapped every
physics step; the final adapter installs a one-use operation after `mj_forward`,
then restores the direct native call for the remaining substeps.

Initial Safari trials retained the same browser process between navigations.
The reference itself varied from 92.984 to 129.049 seconds, so those trials
cannot support a before/after speed claim. The final comparison instead
navigates to an idle page, stops and relaunches Safari, then processes the same
public robot fixture. Restoring an auto-running test page on relaunch is avoided.
Only one calculation runs at a time; builds and other benchmarks are stopped.
The model files are served locally and cached. These are computation measurements,
not an internet download test or a physical-iPhone performance guarantee.

## Results

The final Safari Simulator comparison used the 26.165-second public robot
recording on the available Apple M3 Max. Each run completed the actual visitor
processing and saved-result workflow.

| Measurement | Previous release | This release |
| --- | ---: | ---: |
| Body stage, mean | 89.234 s | 85.812 s |
| Individual body-stage times | 89.919, 88.548 s | 85.684, 85.939 s |
| Complete processing, mean | 99.072 s | 96.165 s |
| Physics binary | 4,632,279 bytes | 4,672,599 bytes |
| Policy WASM memory | 16 MiB | 16 MiB |

This is a **3.8% body-stage improvement**, about 3.4 seconds, and a 2.9%
improvement across the complete workflow. It is not a substantial reduction
from the earlier 90-second wait. The engine still spends most of its time
solving body dynamics and contacts. Compiler and call-boundary changes do not
remove that work. The old and new timing ranges are reported rather than
claiming a device-independent speedup. Two trials per version are a small sample.

The old and new Safari runs have exactly equal processed audio, neural counts,
population capture, spatial capture, body positions and orientations, timestamps,
commands, states, events and movement metrics. Wall time and implementation
provenance intentionally differ. Saving and reopening the result also pass.
The complete comparison passes in desktop Chromium too; its timings overlapped
other validation work and are excluded from speed claims. Its saved result was
reopened and played through the final post-sound frame with no browser errors.
Cancellation during the body stage completed in approximately 1 ms in Safari.

The release checks include:

- 181 Python and 87 JavaScript tests, plus Ruff lint and formatting.
- Exact intermediate joint states, controls, accelerations, solver warm-start
  state, constraint forces, sensors and controller observations.
- Invalidation after a timestep/integrator/model/data change or failed forward
  pass, and exact recovery from invalid position/velocity auto-resets.
- A complete 550-frame controlled sequence exercising walking, turning, takeoff,
  flight, landing and standing.
- Exact reproduction of all 3,230 frames of the saved 64.6-second silence run.
- The existing Python/WASM fixture check at its unchanged tolerances. Native
  Python and WASM are not bit-identical; old/new exactness is within one browser.
- Two independent links reproducing both engine files byte for byte.

Reports are in `experiments/body-speed-v2/`. These checks are evidence for the
specified inputs and state boundaries, not a universal proof for every possible
trajectory or a test on a physical iPhone. The preliminary, inconsistent timing
runs are retained separately from the final comparison.

## Rebuild

Use the Emscripten 4.0.10, CMake and TypeScript toolchain documented in
[BODY-SPEED.md](BODY-SPEED.md). From a clean checkout of the pinned MuJoCo source:

```sh
python scripts/build_mujoco_simd.py --source /tmp/mujoco-body-build \
  --build /tmp/mujoco-body-build/build --output /tmp/body-physics-build \
  --full-lto --body-step
node --test tests/body-physics.test.mjs tests/body-stepping.test.mjs
node scripts/check_body_physics.mjs output/body-speed-v2/physics-equivalence.json
```

The build script rejects unrelated source edits. The tiny binding is checked
against the repository copy before compiling. Hashes must match
`static/body-physics.js`; a changed compiler or binary requires qualification
again. The original official binary and the saved silence contract are retained
as references, and historical results are not overwritten.

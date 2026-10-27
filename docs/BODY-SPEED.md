# Faster body calculation, 27 October 2026

Visitor recordings still run locally. This change compiles the existing MuJoCo
3.14.0 engine with standard WebAssembly SIMD instructions. It retains the same
20,000 physics steps per simulated second, solver settings, collision geometry,
controller networks, controller observations, neural-to-body adapter, wingbeat
patterns and recorded poses. Neither the connectome nor the receiver changes.

## Implementation boundary

The engine source is pinned to commit
`9ecbb9d7b5ee623f54745638d36799ff90e6f7cd`. The compiler is Emscripten 4.0.10,
the compiler used by the original distribution. The build adds `-msimd128` and
`-ffp-contract=off`, with Release `-O3`. It does not enable fast math or relaxed
SIMD and makes no changes to the physics source. The original assertions and
exception handling remain enabled. SIMD operates on independent values together;
it does not reduce numerical precision or the number of integration steps.

Removing debugging and source-map output also lets Emscripten run its ordinary
post-link optimizations. The physics download falls from 10,313,475 to
4,632,279 bytes. The model and policy assets are unchanged and keep their cache
keys. The worker checks the new binary's digest before executing it.

The two controller networks share one 16 MiB WASM memory instead of reserving
16 MiB each. `body-policy-bundle.js` copies their original float32 weights into
disjoint regions and offsets the existing metadata. Both use the unchanged
`BodyPolicy.infer` function. Because walking and flight inference are serial
inside one worker, they can reuse its scratch buffers; returned action arrays
remain independent copies. Tests compare every weight and alternate both
controllers against the separate-memory implementation. Sharing must not be
used for concurrent inference on the same memory.

`body-physics.js` names the reference binary and qualified replacement. The
model manifest and saved-silence contract remain unchanged; the faster build is
an alternative implementation of that contract. Worker initialization and each
new body result record its compiler, source commit and binary hash separately.
The loader refuses a different reference physics hash. Historical recordings
and curated playback artifacts are not overwritten or recomputed.

## Qualification

Two complete Safari Simulator runs per version used the same 26.165-second
public robot recording and a warm model cache. No other benchmark or build ran
alongside them.

| Measurement | Before | After |
| --- | ---: | ---: |
| Body calculation, mean | 93.889 s | 90.416 s |
| Whole processing workflow, mean | 104.177 s | 100.389 s |
| Physics binary download | 10,313,475 bytes | 4,632,279 bytes |
| Policy WASM memory | 32 MiB | 16 MiB |

The body calculation improved by 3.7% in this small sample. Individual body
times were 94.826 and 92.952 seconds before, 92.289 and 88.543 seconds after.
This is a modest speed improvement; the stronger benefits are the smaller
first download and lower controller memory use. Total browser memory is not
halved. The physics memory itself rose by one 64 KiB page. Cancellation during
body processing completed in 1 ms in the simulator and left no partial result.

The unit suite checks exact joint positions, velocities, actuator state,
controls, acceleration, solver warm-start state, sensors, poses and both policy
observation formats against the original binary. The slow release script also
compares a complete controlled movement sequence and all 3,230 frames of the
saved silence trajectory, including commands, transitions and movement metrics.
Full Safari recording trials compare processed audio, neural capture, body
poses and measurements, then check saving and reopening the result.
The same complete comparison passes in the desktop Chromium browser. Its
verification runs overlapped other checks, so their timings are not used as
benchmark results. The existing Python/WASM fixture check also passes at its
unchanged tolerances; native Python and WASM were never
bit-identical. The unchanged-result claim here compares the old and new WASM
implementations within the same browser.

The complete suites pass: 181 Python tests and 83 JavaScript tests. Rebuilding
with the documented script reproduced both committed engine files byte for
byte. A newly processed recording was reopened and replayed to its final
post-sound frame in the desktop interface without browser errors.

Timing measurements are recorded in `experiments/body-speed-v1/`. Simulator
measurements run on the available Apple M3 Max, not a physical iPhone. Download
time depends on the connection; cached local tests measure calculation rather
than an internet transfer. Exact agreement on these cases is a release check,
not a claim that two different numerical engines are universally equivalent.

## Rejected shortcut

Reusing the position/velocity stage between `mj_forward` and `mj_step2` looked
plausible but changed recorded trajectories. Both attempted variants were
rejected. The production runtime still calls the same complete `mj_step` and
`mj_forward` sequence. The rejected diagnostic hashes are retained with the
performance evidence.

A separate experiment moved the substep/sensor-averaging loop into a compiled
binding. Its outputs matched but it did not improve the full Safari workflow,
so it is not part of the release.

## Rebuild and verify

Normal builds use the committed binary and need no extra dependencies. For an
engine rebuild, install Emscripten 4.0.10, CMake 3.31.6 and TypeScript 5.8.3 in a
temporary development environment. Activate Emscripten and put `cmake` and
`tsc` on PATH, then:

```sh
git clone https://github.com/google-deepmind/mujoco.git /tmp/mujoco-body-build
git -C /tmp/mujoco-body-build checkout --detach 9ecbb9d7b5ee623f54745638d36799ff90e6f7cd
python scripts/build_mujoco_simd.py --source /tmp/mujoco-body-build \
  --build /tmp/mujoco-body-build/build --output /tmp/body-physics-build
node --test tests/body-physics.test.mjs
node scripts/check_body_physics.mjs
```

The build script checks the source revision and compiler version, rejects
unrelated tracked source changes, and prints the output sizes and checksums.
Compare them with `static/body-physics.js` before replacing any committed files.
The full qualification must pass again after a compiler or source change.

Upstream references: [MuJoCo WASM build instructions](https://github.com/google-deepmind/mujoco/blob/3.14.0/wasm/README.md)
and [its WASM build configuration](https://github.com/google-deepmind/mujoco/blob/3.14.0/wasm/CMakeLists.txt).

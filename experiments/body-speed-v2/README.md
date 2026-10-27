# Body calculation checks, 27 October 2026

`comparison.json` is the final performance comparison against release
`6cb20e87f22e5caba9447bfabab4d17c53310fc2`. The four `safari-clean-*` reports
use a fresh Safari process each time, restored to an idle page before the trial.
Two runs per version are a small sample. This is iOS Simulator on an Apple M3 Max,
not a physical iPhone. Only the existing public robot recording was used.

The reports record audio, neural and body digests from the actual visitor
processing workflow, as well as saving/reopening checks. Desktop runs and the
long physics qualification overlapped other checks: their times are not used
for speed claims. Cancellation was checked during movement calculation.

`preliminary/` retains exploratory timings, including the rejected 7 MB
aggressive-inlining build and the original adapter that wrapped every substep.
The long-lived Safari process varied substantially even for the unchanged
reference. These trials are excluded from the final speed comparison. Their
file names preserve the testing sequence, not independent causal findings.

`physics-equivalence.json` checks the original official WASM engine against the
final engine plus adapter for a controlled transition sequence, and checks the
entire saved silence trajectory. Re-run with:

```sh
node --test tests/body-physics.test.mjs tests/body-stepping.test.mjs
node scripts/check_body_physics.mjs /tmp/body-physics-equivalence.json
```

The complete test suite and exact build commands are documented in
[the method note](../../docs/BODY-SPEED-V2.md). `reproducible-build.json` records
two independent links that produced the same loader and WASM file.

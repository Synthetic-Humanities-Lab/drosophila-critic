# Full-connectome browser benchmark

The benchmark is independent of the recorded public encounter. The encounter
fetches only audio, aggregate measurements and recorded spatial samples; it
never loads connectivity or starts a simulation worker.

## Implementation and upstream audit

Audited upstream `world/src/connectome.ts` at
`f5850664c64b461cf28d1fe8101ede69b5b37074`, SHA256
`3d1776da0b2f7a2243bcc2e6ed6569073a823d6629da95d6e9f4946fd79606bd`.
Its export rounds connection weights; its update supports additional gain and
input terms. We retain the worker/typed-array structure, but implement only the
pinned original FlyBrain CPU rule and do not import the broader world runtime.
The original equations, parameters and model remain the reference, not latest
upstream behavior. See `vendor/fly.ai/LICENSE` for upstream MIT licensing.

Connectivity is exported as original Float32 weights and UInt32 CSC indices,
gzip-compressed losslessly in 24 MiB raw chunks. Both compressed chunks and
reassembled arrays have SHA256 checksums. Transfer is 138,576,365 bytes (132.2
MiB); decoded connectivity is 205,330,308 bytes (195.8 MiB). No quantization,
pruning or reduced network. Full metadata is not needed to run the brain.

The JS update preserves four accumulation partitions, Float32 rounding points,
Float64 tonic addition, reset and threshold order. The seeded generator is PCG64
with eight base-65536 limbs; initial SeedSequence states for seeds 1101–1104
come from pinned NumPy, not a guessed seed conversion. Tests compare exact
random doubles; the browser checks every voltage and spike array in 100 full
network steps, both with supplied noise and independently generated PCG64 noise.

The first exploratory timing used a simpler PRNG. It is superseded and must not
be used to qualify visitor processing. Final measurements must use PCG64.

## Reproduce

```sh
PYTHONPATH=. .venv/bin/python scripts/export_browser_benchmark.py
.venv/bin/python scripts/export_replay.py
cp -R results/browser-benchmark dist/benchmark-data
.venv/bin/python -m http.server 8777 --directory dist
```

Open `http://127.0.0.1:8777/browser-benchmark.html`; load the model, validate,
then benchmark both recordings. Save the displayed report. The worker supports
initialize, validate, simulate and cancel. All execution is local, with no upload.
The large export is kept in ignored `results/`; CI does not publish it.

Simulation times include warmup, baseline and tail. Qualification compares wall
clock with twice the **spoken recording duration**, excluding initial download.
Reported typed-array allocation is not total browser memory or measured peak.
The browser used here does not provide a reliable cross-worker peak-memory API;
peak memory must be reported unavailable, not inferred from array lengths.
A mobile-width screenshot is not a mobile-hardware performance measurement.

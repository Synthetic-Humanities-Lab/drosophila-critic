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
The benchmark fixtures remain in ignored `results/`. After qualification,
`PYTHONPATH=. .venv/bin/python scripts/prepare_browser_release.py` creates the
public `static/browser-model-v1` package; CI publishes those lossless chunks.
The encounter never requests them. Only an explicit click on `listen.html` does.

Simulation times include warmup, baseline and tail. Qualification compares wall
clock with twice the **spoken recording duration**, excluding initial download.
Reported typed-array allocation is not total browser memory or measured peak.
The browser used here does not provide a reliable cross-worker peak-memory API;
peak memory must be reported unavailable, not inferred from array lengths.
A mobile-width screenshot is not a mobile-hardware performance measurement.


## Qualified desktop result

The saved report is `experiments/browser-v1/benchmark.json`. Chromium 154 on
macOS, reporting 14 hardware threads and 32 GB device memory:

| Measurement | Result |
| --- | --- |
| Robot, full run including baseline/tail | 40.4114 s (26.1653 s spoken) |
| Human, full run including baseline/tail | 65.1361 s (45.1 s spoken) |
| Localhost model initialization | 1.5442 s; not an internet-download estimate |
| Transfer | 138,576,365 bytes |
| Fixed working arrays lower bound | 208,664,308 bytes |
| Peak browser/worker memory | unavailable |
| Supplied-noise fixture | 100 steps, exact voltages and spikes |
| Independently generated PCG64 fixture | 100 steps, exact voltages and spikes |
| Complete poem global-count parity with Python | exact, 1,539 / 2,485 steps |

Full-run count parity is in `full-run-count-parity.json`; unlike the shorter
fixture it checks aggregate spike counts, not every final neuron voltage.
Cancellation was exercised during a run and returned controls immediately.
Both performance limits pass on this machine. Safari, Firefox, lower-memory
computers and mobile hardware have not been benchmarked. The archived report's
`visitor_recording_enabled: false` records the benchmark page's state at capture,
not the subsequent release decision.

## Local visitor experiment

`listen.html` offers recording, file selection and a public-example check. It
runs the reference and visitor waveform, each with matched silence, from seed
1101. Original weights are hashed after each run. It uses the same displacement
receiver and numerical configuration; audio is pairwise RMS matched without
compression. Encoding, group counts, hashes, configuration and the numeric-only
reading input can be saved as JSON. Audio and results stay in browser memory.
Model chunks alone may be cached by version. No backend, upload or telemetry
is used. Clear site data to remove the cached model.

The microphone stops at 59 seconds to leave room for codec padding within the
60-second decoded-audio limit. Microphone hardware and browser resampling remain
uncontrolled experimental variables. A single-run result carries no replicated
claim. The visitor page provides a response trace, not the curated 3D staging.

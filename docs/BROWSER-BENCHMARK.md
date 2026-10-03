# Full-connectome browser benchmark

The development benchmark is separate from recorded playback. Curated playback
fetches audio, measurements and recorded spatial samples. Only choosing to
process a visitor recording loads connectivity and starts a simulation worker.

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

The finalization build replaces floating-point remainder with an exact low-16-bit
mask in the generator's limb recurrence. Each intermediate is an exact integer
below 2^36; the carry calculation and output sequence are unchanged. Tests hash
one million NumPy doubles for each of all four supported seeds and check their
final generator states, in addition to full-network equivalence checks.

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
then run the silence/pulse diagnostics and benchmark both recordings. Save the
report. The compact on-screen report retains hashes rather than rendering
millions of spike indices into the DOM. The download retains the full output.
The worker supports
initialize, validate, simulate and cancel. All execution is local, with no upload.
The benchmark fixtures remain in ignored `results/`. After qualification,
`PYTHONPATH=. .venv/bin/python scripts/prepare_browser_release.py` creates the
public `static/browser-model-v1` package; CI publishes those lossless chunks.
Only an explicit processing click in the shared encounter requests them.
`listen.html` redirects to that encounter's recording section.

Simulation times include warmup, baseline and tail. Qualification compares wall
clock with twice the **spoken recording duration**, excluding initial download.
Reported typed-array allocation is not total browser memory or measured peak.
The browser used here does not provide a reliable cross-worker peak-memory API;
peak memory must be reported unavailable, not inferred from array lengths.
A mobile-width screenshot is not a mobile-hardware performance measurement.


## Original qualification and current capture checks

The original report is `experiments/browser-v1/benchmark.json`. Chromium 154 on
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
Both performance limits passed in that run. Safari, Firefox, lower-memory
computers and mobile hardware have not been benchmarked. The archived report's
`visitor_recording_enabled: false` records the benchmark page's state at capture,
not the subsequent release decision.

The current worker additionally records ten population counts at every step
and actual spikes in a fixed 12,000-cell sample, binned at 100 ms. These observers
do not consume random numbers or change the neural update.

`experiments/browser-v2/benchmark-summary.json` records a complete run with
capture: 39.8361 s robot, 62.6975 s human, 1.8878 s localhost initialization.
Both remained under twice the spoken duration on this machine. A second run
while other QA pages were active took 57.7504/94.4345 s and missed that time
target (`benchmark-capture.json`). Both reports are retained; the benchmark is
not a speed guarantee under competing load or browser scheduling. A repeat with
other QA playback paused also missed the target (57.6622/93.4291 s,
`benchmark-repeat.json`); closing test pages alone did not resolve it.

The final implementation removes floating-point remainder from PCG64's hot
loop and skips empty population memberships during capture. The retained
`benchmark-release.json` passes both performance gates: **46.3815 s robot and
40.3687 s human**, including neural baseline/tail and spatial capture. Model
initialization took 1.4376 s on localhost. The different warm/cold timing of the
two runs is not a comparison of poem effects. All response hashes remain exact.

The second report adds response hashes. `capture-parity.json` compares them
against the saved original Python runs: **every global count, every named-group
count and every sampled spike bin matches exactly** for both poems, including
the final partial bin. Reproduce with
`.venv/bin/python scripts/check_browser_capture.py` after saving the browser
summary to `experiments/browser-v2/benchmark-release.json`. To inspect an earlier
report, pass `--report PATH`; old reports remain unchanged.

`diagnostic-summary.json` records one second containing a 200 Hz tone pulse,
silence, and a repeated identical pulse. Silence has spontaneous firing; the
pulse changes downstream activity by +0.38545 spikes/s/cell over its one-second
window. The repeated pulse gives identical global, population and spatial
hashes. This establishes software sensitivity and repeatability, not a
physiological calibration or an interpretation of a fly's feelings.

## Local visitor experiment

The main encounter offers recording, file selection and a public-example check.
It runs the visitor waveform and its equal-duration silence from seed 1101.
There is no compulsory robot comparison. Original weights are hashed after
each run. The receiver and neural configuration remain the same. Audio receives
linear gain to RMS 0.05, lowered if its peak would exceed 0.95; actual levels
are saved. Pauses and dynamics remain, with no compression.

The common replay contains original coordinates and newly computed spikes,
aggregate measurements and mechanical input traces. Encoding, group counts,
spatial sample, hashes and configuration are exportable as JSON; original and
processed audio have separate downloads. Data stays in browser memory. Model
chunks alone may be cached by version. No backend, upload or telemetry is used.
Clear site data to remove the cached model. Source checksum failures, failed
initialization, cancellation and replacement cannot silently reuse old spikes.

The microphone stops at 59 seconds to leave room for codec padding within the
60-second decoded-audio limit. Microphone hardware and browser resampling remain
uncontrolled experimental variables. A single-run result carries no replicated
claim. The visitor uses the same scene and controls as the examples; arbitrary
audio receives no automatic poem-line timing. Microphone capture and file-picker
QA limits are recorded in [FINALIZATION-QA.md](FINALIZATION-QA.md).

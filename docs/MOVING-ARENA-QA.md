# Moving-arena release checks

Tested 3 October 2026. This release adds computed body movement to the existing
frozen neural simulation. It does not validate the adapter as a prediction of
living-fly behaviour. [Modeling choices](NEURAL-BODY-ADAPTER.md).

## What runs

The articulated flybody anatomy has 69 bodies and 65 actuators. The original
walking and flight mean policies remain frozen. A separate supervisor handles
standing, wing deployment, takeoff, contact-based landing and arena corrections.
The physics timestep is 50 μs, independent of rendering. There are no external
root forces or position resets after initialization.

The [controlled proof](https://synthetic-humanities-lab.github.io/drosophila-critic/body-proof.html)
walks, turns, takes off, flies and lands in one continuous run. Its
[commands, events and metrics](../experiments/body-controller-v2/controller-proof.json)
and [complete poses](../experiments/encounter-v3/controller-proof.json.gz) are saved.
It includes 2.50 seconds actually airborne; the total is 11 seconds. A 60 ms
inversion transient during contact is recorded, not hidden. No persistent
inversion, escape or failed run was accepted. Contact transitions can still
look abrupt; the supervisor is an engineering extension to the published tasks.

The [original flight task qualification](../experiments/body-controller-v2/flight-qualification.json)
checks straight flight, turning and an identical repeat with the supplied
wingbeat data. These precede the combined arena supervisor.

## Neural dependence and curated evidence

Every spike in the selected annotated motor populations contributes to the
adapter. None comes from the 12,000-cell visual sample. The original auditory
receiver, neural weights, timestep, noise and four seed values are unchanged.
The adapter's gains were fixed using silence and controlled input. Later body
changes address falling/turning failures shared across inputs, not desired poem
contrasts; the final combined controller was applied to the entire batch.

- 16 complete trajectories: two readings × sound/silence × four seeds.
- All 16 native reruns have identical position **and quaternion** bytes:
  [repeatability report](../experiments/body-controller-v2/native-repeatability.json).
- Controlled walking stimulation changes movement; clamping its input to zero
  restores the identical zero-input body trajectory:
  [causal check](../experiments/body-controller-v2/body-causality.json).
- Python and JavaScript adapter tests exercise the selected signals, smoothing,
  saturation, takeoff rearming, landing contact, and separately logged boundaries.
- Curated replay uses seed 1101 in both body and neural displays. Measurements
  below it aggregate four runs; they do not describe only the visible animal.

The [paired movement report](../experiments/encounter-v3/movement-summary.json)
retains each seed and full ranges. For the human reading, post-voice horizontal
travel averages 13.9 cm versus 8.1 cm in silence, higher in all four runs.
Walking distance, flight time and turning do not retain one direction in every
human pair. All four robot movement contrasts change direction between seeds.
There is no overall winner, quality score or claim of a physiological effect.
Durations differ between readers; each is compared with its own silence control.

## Python / browser numerical checks

The official single-threaded MuJoCo WebAssembly runtime is version 3.14.0, matching
Python. Original float32 mean-policy weights are exported without quantization.
The browser's SIMD matrix multiply is an inference implementation, not a new
trained controller. TensorFlow reduction order and native/WASM physics are not
bit-identical.

| Check | Result |
| --- | --- |
| Original SavedModels versus exported Python policy, 20 fixtures each | Passed; maximum applied-action error 0.0000637 walking, 0.000000596 flight |
| SavedModels versus browser policy, 20 fixtures each | Passed; maximum applied walking-action error 0.0000433 |
| 25 body-observation fixtures including flight state and wrapped heading | Maximum absolute difference 3.20×10⁻¹⁶ |
| 40 zero-control physics steps | Maximum state difference 7.47×10⁻¹⁰ |
| 80 nonzero-actuator physics steps | Position/orientation difference 1.17×10⁻¹⁰; velocity 2.26×10⁻⁷; actuator state 1.74×10⁻¹⁷ |
| One-second browser body repeat | Identical full joint state |

[Python policy report](../experiments/body-controller-v2/python-policy-parity.json),
[browser policy report](../experiments/body-controller-v2/browser-policy-parity.json),
[observation/physics fixtures](../experiments/body-controller-v2/body-validation.json),
[browser runtime report](../experiments/body-controller-v2/browser-runtime-parity.json).

Physics tolerances are explicit: 10⁻⁸ for qpos, 10⁻⁶ for qvel, and 10⁻¹² for
actuator state in the nonzero-control check. qpos includes cm and angles; qvel
includes cm/s and rad/s. The largest discrepancy is in velocity, while the
corresponding pose error remains about 10⁻¹⁰. These finite-precision differences
can grow across long, contact-rich trajectories. This is **short-step numerical
agreement and within-runtime repeatability**, not identical native/browser
full-poem trajectories. Compare paired conditions within the same runtime.

## Local visitor processing

Two complete 60-second tests ran the public robot recording repeated to 60 s,
with each test independently computing its own neural response, equal-duration
silence and two body trajectories. They passed the 300-second processing limit.
Models were cached. Initial network transfer time depends on the connection.

| Stage | First run | Repeat |
| --- | ---: | ---: |
| Model initialization/loading from cache | 2.17 s | 2.29 s |
| Neural pair | 55.26 s | 54.77 s |
| Body pair | 219.23 s | 220.56 s |
| Complete processing | **276.91 s** | **277.86 s** |

Both conditions have identical saved body-position hashes across the two tests.
Reports: [first](../experiments/body-controller-v2/browser-60s-first.json),
[repeat](../experiments/body-controller-v2/browser-60s-repeat.json),
[comparison](../experiments/body-controller-v2/browser-repeatability.json).
The ordinary visitor interface was also used with the complete 26.17-second
robot example; its new trajectory and own silence control replayed to the end,
including the post-voice interval. No curated trajectory was substituted.

Environment: available macOS desktop; browser-reported Chromium 154, 14 hardware
threads, 32 GB device memory. The OS/processor model was not independently
queried. Safari, Firefox, Windows, low-memory desktops and physical mobile
devices are **not qualified** by these measurements. Mobile visitor processing
remained disabled in that build; recorded playback remained available. The later
[experimental mobile release](MOBILE-RECORDING.md) adds sequential processing
and iOS Simulator checks; it does not retroactively qualify physical phones.

The body-processing download is 16,934,399 bytes, including its runtime and
licenses. Combined with the existing 138,576,365-byte neural export, this is
155,510,764 bytes, excluding small app modules/manifests and the separate 6.7 MB
visual anatomy. The original policy source archive is available for licensing
and reproduction but is not downloaded by visitor processing.

Each body worker has a 17,563,648-byte MuJoCo linear memory and 33,554,432 bytes of
policy linear memory. Two body workers run independently. These figures exclude
neural workers, JavaScript objects, decoded audio and retained trajectories;
**browser-wide peak memory was not measurable through the available API**.
The app releases the simulation workers after completion or cancellation.

Cancellation during actual body calculation returned in 0.8 ms and terminated
all simulation workers: [report](../experiments/body-controller-v2/browser-cancellation.json).
Errors, asset checksum failures and invalid body trajectories stop processing;
there is no upload or replacement animation. No microphone permission was
requested for these tests; public audio fixtures were used.

## Interface and regressions

- 170 Python tests and 34 JavaScript tests passed. Two existing FastAPI/Starlette
  deprecation warnings remain. Changed Python files pass Ruff.
- Full curated playback, reader changes, corresponding stanza selection,
  seeking, silence and the post-voice window were inspected in the browser.
- Body poses, sound input, neural display and highlighting follow one audio
  clock. Seeking reads the saved pose; no renderer physics is restarted.
- Actual desktop and 390 px mobile layouts were inspected. The fly remains
  above the neural panel on mobile; no horizontal overflow was found.
- Reduced-motion playback uses a fixed camera and turns off neural flashes;
  wingbeats use a stable exposure from four published wing-pattern poses.
- Explicit 2D mode retains the position map and traces. A deliberate HTTP 404
  for the anatomy asset also retained functional audio, neural activity and map.
- Curated playback loads saved responses and visual assets, not the connectome,
  policy weights or physics runtime. Visitor model loading follows the explicit
  processing button.

Before: [previous scene](images/arena-before-desktop.jpg).
After: [desktop](images/arena-after-desktop.jpg), [mobile](images/arena-after-mobile.jpg).
Actual scene recordings: [desktop](images/drosophila-arena-desktop.webm),
[mobile](images/drosophila-arena-mobile.webm),
[controller proof](images/flybody-controller-proof.webm).
The scene recordings capture the rendered animal and neural canvases with time
and state captions; they are not browser-chrome recordings. Screenshots document
the surrounding interface.

The published visitor flow also passed using the complete public robot example:
2.68 seconds loading, 26.78 seconds for the neural pair and 107.81 seconds for the
body pair; **137.38 seconds total**. Its fresh body trajectories replayed through
the post-sound interval. [Deployed visitor evidence](../experiments/body-controller-v2/deployed-visitor.json).

The deployed curated page's [resource inventory](../experiments/body-controller-v2/deployed-replay-assets.json)
contains saved poses and anatomy but no processing models. Full human, robot,
silence and visitor playback, passage switching, the controller proof and
reduced-motion controls were checked on the published site.
Deployment details are in [release status](MOVING-ARENA-STATUS.md).

An additional live-site file-picker test with the public human WAV was blocked
by browser approval review, which reported declined permission. It was stopped,
without an alternate upload route. The built-in public robot-example visitor
flow passed on the deployed site; the local processing benchmarks and file/codec
unit checks do not substitute for this uncompleted live-site file-picker test.

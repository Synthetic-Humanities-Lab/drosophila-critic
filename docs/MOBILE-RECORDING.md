# Mobile visitor recordings — 4 October 2026

Visitor recording and file selection are now available on capable mobile
browsers. This is an **experimental mobile release**, not a qualification of
every iPhone. It remains entirely local: microphone/audio files and calculated
results are never uploaded. Processing starts only after **READ TO THE FLY**.

## What changed

- Replaced the blanket phone/tablet exclusion with feature checks for secure
  context, workers, WebAssembly, gzip decompression, hashing and Web Audio.
- Phones, iPads using a desktop user agent, and browsers reporting at most
  4 GB of memory use one neural worker for sound and silence in sequence. Each
  request resets voltages, previous spikes and the same seeded RNG. The body
  worker is also reused; each condition creates fresh physics, adapter and
  supervisor state. Other desktops retain the existing parallel schedule.
- Both schedules release connectivity **before** initializing body physics,
  and release all simulation workers on success, failure or cancellation.
- Model chunks are copied into their final array as they are decoded. The
  loader no longer retains every decoded chunk alongside a second assembled
  copy. Compressed and reconstructed SHA-256 checks remain enforced.
- Decoding uses a 48 kHz `OfflineAudioContext`. A recording's `onstop` callback
  can decode without trying to resume a playback context outside a user gesture.
  Playback still starts from an explicit user action.
- The recorder selects WebM/Opus where the browser advertises it, then MP4/AAC,
  then its default. Safari's [MediaRecorder documentation](https://webkit.org/blog/11353/mediarecorder-api/)
  describes MP4 support; [Safari 18.4](https://webkit.org/blog/16574/webkit-features-in-safari-18-4/)
  added WebM/Opus recording. The receiver always uses decoded, normalized PCM.
- **Save recording** is available before processing. An optional screen wake
  lock helps prevent idle screen lock while recording or computing, is released
  on completion/cancellation, and is reacquired when a busy page becomes visible.
  Processing still works if the browser declines that optional request.

The connectome, weights, timestep, auditory receiver, normalization, seed,
body policies, movement adapter, arena and display scales are unchanged.
Saved evidence includes `processing.execution` (`sequential` or `parallel`).
One recording is still compared with its own equal-duration silence control.

## Measured checks

Safari 26.5 in Xcode's **iPhone 17 simulator / iOS 26.5**, running on the available
Mac, completed the public 26.1653-second robot recording through the actual
`RecordingPanel` preparation/processing code and both simulation stages.
The local QA harness supplied a public fixture; it did not request a microphone.
This uses iOS Safari, rather than a desktop browser resized to phone dimensions.
It is nevertheless **not physical iPhone hardware**.

| Check | Result |
| --- | --- |
| Full-network Python fixture, supplied noise | Exact voltage and spike hashes for all 100 steps |
| Full-network fixture, browser-generated PCG64 | Exact; no mismatches |
| Full public recording plus matched silence | Complete, 1,539 steps per condition |
| Body trajectories for both conditions | Complete; no failed trajectory replaced by animation |
| Safari sequential vs Chromium desktop parallel | Identical normalized audio, global counts, population counts, sampled firing, body positions and orientations |
| AAC/M4A file decoding | Complete 26.165-second file decoded at 48 kHz |
| Cancellation in Safari during neural processing | Returned in approximately 1 ms; workers stopped; no result substituted |
| JavaScript regression suite | 54 passing tests |
| Python suite | 173 passing tests; two existing dependency deprecation warnings |

The ordinary desktop interface also processed the complete public robot fixture,
offered its own result for replay, and exported its response JSON. The comparison
above uses that exported result, not values invented for the QA display.

Safari simulator timings: 1.367 s to initialize the cached/local model, 84.110 s
for the neural pair, 281.398 s for the body pair, **366.963 s total**. Desktop
Chromium's parallel run took 177.997 s in this session. Some desktop testing
overlapped the simulator run. These are compatibility observations on one host,
not isolated performance benchmarks or predictions for a visitor's phone.
The desktop's historical five-minute/60-second acceptance does not apply to
mobile. Start with a short recording and keep the browser page open.

The neural working-array lower bound is 208,664,308 bytes for one worker,
instead of two simultaneous copies. A body worker reports 17,563,648 bytes of
MuJoCo linear memory and 33,554,432 bytes of policy memory. These numbers exclude
JavaScript objects, audio, graphics and retained trajectories; **peak browser
memory was not measured**. The model download remains approximately 156 MB.
There is no smaller or reduced-connectome mobile substitute.

Evidence:

- [Safari full recording and Python-equivalence report](../experiments/mobile-v1/safari-simulator-robot.json)
- [Desktop result and exact cross-engine comparison](../experiments/mobile-v1/chromium-robot.json)
- [Safari M4A and cancellation report](../experiments/mobile-v1/safari-m4a-cancel.json)

## Remaining device checks

Physical microphone permission/capture, Bluetooth inputs, screen lock or phone
calls during capture, low-memory termination and battery/thermal behavior need
testing on actual phones. The code tests recorder selection, stopped-recording
decoding, late cancellation and delayed wake-lock acquisition, but those tests
do not replace microphone hardware checks. A killed/reloaded page loses its
in-memory audio and result; save the original before starting a long run.

To check a phone, open the HTTPS app, choose **YOUR VOICE**, record a short clip
or select an M4A from Files, stop and listen back, then choose **READ TO THE FLY**.
Confirm the result plays your audio with its newly calculated neural response
and movement, then compare with silence. Record the iPhone model, iOS version,
clip length and exported `processing` timings before making a device-speed claim.

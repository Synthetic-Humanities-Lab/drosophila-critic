# Loading changes, 22 October 2026

The encounter now transfers less data, starts necessary downloads earlier, and
reuses recordings during navigation. Anatomy, materials, shadows, audio samples,
neuron sampling, recorded movement, simulation parameters and policies are unchanged.

## Measured first loads

Two sequential cold loads per reader and build in Chromium 155 on the available
Mac. A local HTTP server imposed an aggregate 10 Mbit/s and 80 ms delay per request,
with browser caching disabled. Text and GLB responses were gzip-compressed, as
observed on GitHub Pages. Timings run from navigation to enabled PLAY **with the
fly anatomy loaded**, not just the appearance of the page or an enabled button.
They are controlled comparisons, not predicted times for every visitor.

| Recording | Previous load | New load | Shorter wait | Previous transfer | New transfer |
| --- | ---: | ---: | ---: | ---: | ---: |
| Robot | 13.50 s | 8.80 s | 34.8% | 14.78 MB | 9.63 MB |
| Human | 19.25 s | 11.29 s | 41.4% | 21.30 MB | 13.22 MB |

Transfers count encoded resource bodies through first readiness, excluding the
test report, favicon and page HTML. MB means 1,000,000 bytes. The two new robot
trials ranged from 8.68 to 8.92 seconds; human trials were 11.29 seconds each.
Raw request timings, sizes and conditions are in
[the comparison evidence](../experiments/loading-v1/comparison.json).

One already-loaded robot stanza change took 2.41 seconds before and 0.051 seconds
after. The former fetched another 2.51 MB waveform; the latter made no new audio
request. This is one navigation observation, including first audio decoding,
not a device-wide latency guarantee. Unit checks also verify reuse of the
decoded buffer when switching between the two voices.

## What changed

`scripts/pack_playback.py` makes delivery copies during export. Each body copy
stores the same timestamps, positions and quaternions as little-endian IEEE-754
float64 arrays. Bytes of the same significance are grouped before gzip, which
compresses them more effectively. There is no rounding, quantization,
downsampling, interpolation change or dropped frame. Commands, states, metrics,
events and provenance remain JSON metadata. The browser reconstructs the existing
playback shape using float64 views. The robot sound trajectory shrinks from
6,339,014 to 2,079,550 bytes; the human from 10,303,208 to approximately 3.44 MB.

The two WAV files are gzip-compressed without changing the original PCM. No lossy
audio codec is introduced. Delivery filenames contain content hashes, and the
generated `encounter-v4` manifest records source and delivery checksums. Original
experiment files and the `encounter-v3` manifest remain available and unmodified,
including their published URLs for older open pages. The new edition changes
delivery only; it selects compact copies of the same recorded experiments.

The exporter adds preload hints for the actual entry module's static imports
and the playback manifest. It does not preload workers, connectivity, policies,
silence controls, or the unselected reading. Audio now downloads alongside neural
and movement data instead of waiting until the movement download finishes.

Stanza navigation seeks the existing scene and recording. A bounded two-entry
audio cache reuses downloaded bytes and decoded buffers for reader changes.
Failed downloads are evicted for retry; superseded downloads cannot replace the
active recording. A newly computed visitor recording still replaces its prior
trajectory instead of taking the stanza-only shortcut.

Visitor model loading overlaps at most two requests for small body assets and
saved-control chunks. Control chunks are reassembled in their original order;
connectivity chunks are written to predetermined offsets, then the whole-array
checksum is checked. On desktops, two connectivity chunks may overlap too.
Phones and low-memory devices retain one large connectivity chunk in flight:
each expands to as much as 24 MiB, so speculative mobile parallelism would add
memory pressure. Nothing loads before the visitor explicitly starts processing.

## Verification and limits

- All four displayed curated body trajectories pass bit-for-bit float checks
  against their original recordings. The browser decoder also reproduces the
  original poses and camera path. Malformed/truncated files are rejected.
- Audio compression round-trips the original bytes. Playback tests cover cache
  reuse, retries, superseded loads/decodes, seeking and playback boundaries.
- Real browser workers loaded all 166,700 neurons and original connectivity.
  All 100 Python fixture states matched with supplied noise and with generated
  seeded noise. A controlled pulse sequence produced identical neural counts,
  sampled spikes, body poses, commands, states and movement measurements before
  and after the loader changes. See [numerical checks](../experiments/loading-v1/model-parity.json).
- The mobile layout and compact playback loaded in native Safari 26.5 in the
  iPhone 17 / iOS 26.5 Simulator. This does not measure physical-phone thermals,
  memory pressure or mobile network conditions.
- A three-second excerpt of the public robot recording completed the full
  visitor workflow in that Safari simulator. Neural processing, body processing,
  saved silence, and local save/load passed. This verifies the updated loading
  path, not a new full-poem processing-speed qualification.
- The complete local suites passed: 181 Python tests and 75 JavaScript tests.
  Two existing Python dependency deprecation warnings remain.

The approximately 156 MB first-time processing-model download remains. Its
contents are already compressed and cached; these changes do not approximate
connectivity or remove model data. Calculating a new visitor trajectory still
spends most of its time in MuJoCo physics, as documented in
[the previous CPU profile](LOCAL-PERFORMANCE.md). This release accelerates loading
and navigation; it does not claim to eliminate that computation time.

Rebuild with `python3 scripts/export_replay.py`, then serve `dist/` over localhost
or HTTPS. The packer uses only the Python standard library. Validate with
`node --test tests/*.test.mjs` and `.venv/bin/python -m pytest -q`.

# Curated Blake comparison

A is the fixed Kokoro `af_sarah` synthetic rendering of William Blake's public-domain *The Fly*. B is the poem excerpt read by Denny Sayers for LibriVox (2006). See the original recording provenance in `examples/sayers-source.json` and the shared source manifest in `experiments/delivery-v1/manifest.json` in this repository.

The input WAV files are the previously archived `experiments/delivery-v1/sources/reference.wav` and `human.wav`. Their SHA-256 values appear in `result.json`. They were jointly level-matched again by this protocol; the original archival excerpt preparation is not undone. The B recording is 45.10 seconds; A is 26.165 seconds. These are two particular performances, not a population of speakers.

On 2026-10-01 these were submitted through the new multipart comparison API and run on the original full frozen model. All sixteen recorded weight checks passed. Direct postsynaptic partners show B-minus-A mean silence-subtracted differences of −0.0927, −0.1070, −0.0805 and −0.1047 spikes/s/neuron (four shared seeds). The mean is −0.0962. The temporal separation RMS is 0.5094, versus 0.2501 across-seed standard-deviation RMS on the shared 26.1-second interval. These are descriptive diagnostics, not a significance test.

Descending neurons have mixed directions across seeds. There is no consistent motor disposition inferred. B has lower mean injected drive despite equal whole-file RMS, and lasts longer. Neither observation is removed by the experimental design; the differences cannot be attributed to reader identity alone or to a special semantic response.

`implementation/` preserves the exact analysis and simulation-adapter source used for this run. `implementation-sha256.json` hashes those source snapshots. Original upstream/data hashes are included for every run in `result.json`. Large raw spike/count archives remain in the simulation host's result directory; this static publication contains only the deliberately curated public example and its summarized evidence.

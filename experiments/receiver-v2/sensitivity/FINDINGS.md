# Provisional receiver pilot: findings

97 full-connectome runs completed. Four paired seeds (901–904); same initial-state procedure, noise model, 20 ms neural clock and frozen weights. Exact repeated-input spike check passed. These are model sensitivity results, not physiological validation.

## Poem delivery contrast

Human minus synthetic, after each is corrected against its own same-seed, duration-matched silence. Rates are Hz per neuron during sound; not an overall judgment of a rendition. Different durations and total exposure remain.

| Receiver / strength | Direct partners mean | Seed range | Descending mean | Seed range |
|---|---:|---|---:|---|
| legacy-1 | -0.09766 | -0.10637 to -0.09014 | 0.00231 | -0.02077 to 0.01833 |
| displacement-0.5 | -0.03471 | -0.04422 to -0.02467 | 0.00937 | -0.00837 to 0.04629 |
| displacement-1 | -0.09110 | -0.10455 to -0.08490 | 0.00344 | -0.01954 to 0.02578 |
| displacement-2 | -0.20989 | -0.22901 to -0.19649 | -0.01516 | -0.03418 to 0.00230 |
| velocity-0.5 | -0.03514 | -0.05057 to -0.02382 | 0.00882 | 0.00336 to 0.01329 |
| velocity-1 | -0.10438 | -0.11021 to -0.09736 | 0.01162 | -0.01592 to 0.04262 |
| velocity-2 | -0.24370 | -0.25181 to -0.22987 | -0.00983 | -0.02603 to 0.00513 |

**Direct partners:** the human rendition produces a lower mean silence-corrected rate in all four seeds at every tested setting. This direction survives the limited receiver/strength grid; its magnitude does not. The human input also has a lower average injected drive in every arm. This comparison therefore does not establish a response beyond mean stimulation or a distinct qualitative experience.

**Descending neurons:** no common direction survives all receiver settings and seeds. A positive result at one setting must not be promoted into a stable movement disposition. This pooled readout does not rule out differences in particular descending cells, which were not screened here.

## Controlled frequency contrast

| Receiver | 800 minus 200 Hz: direct partners | Seed range |
|---|---:|---|
| legacy | 0.00000 | 0.00000 to 0.00000 |
| displacement | -0.43117 | -0.50639 to -0.36382 |
| velocity | -0.01401 | -0.06391 to 0.01672 |

The legacy receiver produces identical measured group responses to these equal-amplitude tones. The displacement adapter gives a negative direct-partner contrast in all four seeds. The velocity adapter gives a smaller contrast whose sign varies across seeds. The controlled stimuli establish what this apparatus distinguishes, not the accuracy of its hearing model.

## Decision

Keep these adapters experimental. Frequency content now affects the actual frozen-network input and response, but the two poem recordings have not yielded a receiver-independent descending response. No literary reading is generated. Further work should target a matched physiological input-response reference or a controlled within-recording spectral contrast, rather than selecting whichever engineering gain produces an appealing result.

## Audit and reproduction

See [protocol](PROTOCOL.md), [result JSON](comparison.json), [full injected frames](inputs.json), and [exact executed runner source](runner-source.py.txt). The current executable runner differs from the archived snapshot only by removing an unused import after execution. Existing raw caches retain their original source hashes; a rerun with changed source requires a fresh raw results directory, as documented in the README. Complete spikes and population counts are retained locally in `results/receiver-sensitivity/`.

The force-to-channel model is not inserted in this adapter. No new subtype tuning, adaptation stage, carrier phase locking, or biological current calibration is claimed. See the protocol for the bounded literature check.

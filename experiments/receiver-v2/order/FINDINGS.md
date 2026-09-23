# Equal-drive temporal organization: findings

21 full frozen-connectome runs completed; seeds 1001–1004. Exact repeat passed. The original, reverse and shuffle inputs preserve the entire value distribution and duration. Constant input preserves mean, total and duration only. No recording was altered or newly interpreted.

## What changed?

**Yes: changing only block order changes the downstream temporal trajectory reproducibly in this pilot.** In direct partners, native-time difference patterns correlate with the other three seeds at 0.710–0.737 for reversal and 0.733–0.756 for shuffling. Their input value distributions and durations are identical. This establishes temporal discrimination in the model, without requiring a change in overall mean firing or a memory claim.

Spreading the same stimulation evenly over time reduced direct-partner mean firing relative to the patterned original in all four seeds. Therefore average injected strength alone is insufficient to explain this response. This control changes the input distribution as well as temporal pattern; it cannot establish sensitivity specifically to block order.

Reordering moves the neural trajectory in time. After matching each response block back to its original input block, JONs show a repeating context effect. The downstream results are weak: direct-partner RMS signal/error ratios are about 1.01 (reverse) and 1.14 (shuffle); descending ratios are about 0.95 and 0.98. The direct shuffle similarities are positive but small, including one near zero. This pilot does not demonstrate a robust downstream context pattern. These are descriptive diagnostics, not significance tests or proof of absence.

## Mean-rate differences from original

Units: Hz per neuron, after matched-silence subtraction.

| Condition | Direct partners mean | Seed range | Descending mean | Seed range |
|---|---:|---|---:|---|
| reverse | 0.00299 | -0.00307 to 0.00711 | -0.00312 | -0.01515 to 0.01413 |
| shuffle | -0.00273 | -0.00756 to 0.00064 | -0.00249 | -0.01213 to 0.01381 |
| constant | -0.03989 | -0.04669 to -0.03244 | -0.00721 | -0.02870 to 0.01138 |

The order permutations do not give a common-sign mean-rate difference in either downstream group across all seeds. Shuffling lowers JON mean rate in all four seeds, but that does not by itself establish propagation to a behavioral pathway. One-second tail differences are retained in the JSON and interface; they are not a demonstrated persistent state.

## Same blocks, different preceding contexts

| Order | Population | RMS mean difference | RMS standard error | LOO cosine range |
|---|---|---:|---:|---|
| reverse | JO-A/B input | 0.91406 | 0.43719 | 0.477 to 0.646 |
| reverse | direct JON postsynaptic partners | 0.17195 | 0.16945 | -0.144 to 0.117 |
| reverse | descending_neuron | 0.22439 | 0.23526 | -0.102 to -0.002 |
| shuffle | JO-A/B input | 0.84218 | 0.41378 | 0.536 to 0.599 |
| shuffle | direct JON postsynaptic partners | 0.18506 | 0.16216 | 0.007 to 0.173 |
| shuffle | descending_neuron | 0.23056 | 0.23631 | -0.105 to 0.077 |

LOO compares each seeded difference trajectory with the mean of the other three. Realignment changes the placement of the noise realizations. Ordinary lag, integration and recurrent state can produce context differences; this analysis does not establish learning or long-term memory.

## What this permits us to say

The modeled response depends on more than total stimulation: removing fluctuations changes downstream mean activity. These results do not yet justify an affective distinction between performances based on downstream temporal context. They do not identify a movement disposition or a subjective experience.

Keep the production receiver and literary readings unchanged. Any next test should be motivated by the receiver model or physiological evidence, rather than a search for a setting that produces an appealing interpretation.

## Audit

See [protocol](PROTOCOL.md), [injected values and permutations](inputs.json), and [result JSON](comparison.json). Complete spikes, population counts and individual provenance records are in `results/receiver-order/`. No connectome weights changed. Source, protocol, data and run-artifact hashes are retained.

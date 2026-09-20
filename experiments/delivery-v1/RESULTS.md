# Delivery bench v1 — results

Eight seeds (64–71), seven acoustic conditions, 16 duration-matched silence runs: 72 actual full-connectome simulations. Total recorded simulation runtime: 707 seconds. Every run retained frozen weights. All 16 independently simulated repeat/polarity controls matched reference raw spike arrays exactly.

## Primary rate comparison

Values are paired differences: (condition minus its matched silence) minus (synthetic reference minus its matched silence), Hz per neuron. SD is sample SD across paired seeds.

| Condition | Direct JON partners mean ± SD | Signs +/−/0 | Descending mean ± SD | Signs +/−/0 |
|---|---:|---:|---:|---:|
| human | -0.09517 ± 0.01237 | 0/8/0 | +0.00100 ± 0.01677 | 5/3/0 |
| repeat | +0.00000 ± 0.00000 | 0/0/8 | +0.00000 ± 0.00000 | 0/0/8 |
| polarity | +0.00000 ± 0.00000 | 0/0/8 | +0.00000 ± 0.00000 | 0/0/8 |
| pauses | -0.00149 ± 0.00559 | 3/5/0 | -0.00193 ± 0.02091 | 4/4/0 |
| emphasis | -0.04817 ± 0.00799 | 0/8/0 | +0.00011 ± 0.01597 | 4/4/0 |
| reordered | +0.00014 ± 0.00828 | 5/3/0 | +0.00069 ± 0.01823 | 4/4/0 |

The human and emphasis conditions produce consistently smaller mean direct-downstream rate changes than the reference in this seed ensemble. Pauses and reordering do not meet the prespecified mean-rate consistency rule. None of the nontrivial contrasts meets that rule for the pooled descending population. A pooled mean cannot exclude differences within particular descending types or at particular times.

## Temporal findings (supplementary)

Added after initial mean-rate inspection: RMS of the across-seed mean paired trace versus RMS of the pointwise across-seed sample SD, using complete 100 ms bins within the common audio interval. This is a descriptive signal/variability comparison, not a test with corrected error rates. It compares actual elapsed time, not equivalent lines.

| Condition | Mean paired trace RMS | Seed SD RMS |
|---|---:|---:|
| human | 0.5009 | 0.2385 |
| repeat | 0.0000 | 0.0000 |
| polarity | 0.0000 | 0.0000 |
| pauses | 0.3020 | 0.2303 |
| emphasis | 0.2561 | 0.2476 |
| reordered | 0.4667 | 0.2515 |

The pause and reordering diagnostics change the temporal pattern more than the selected descriptive variability measure, despite unstable mean-rate differences. This is evidence that averaging over the whole poem discards a delivery-sensitive signal in the model. It is not evidence that the system recognizes word order or understands a performance.

## Exposure and remaining limits

| Condition | Waveform RMS | Duration s | Mean injection | Integrated injection | Capped frames |
|---|---:|---:|---:|---:|---:|
| reference | 0.0499985 | 26.165 | 0.1439210 | 3.767851 | 0 |
| human | 0.0499985 | 45.100 | 0.1095415 | 4.940323 | 10 |
| repeat | 0.0499985 | 26.165 | 0.1439210 | 3.767851 | 0 |
| polarity | 0.0499985 | 26.165 | 0.1439210 | 3.767851 | 0 |
| pauses | 0.0499985 | 26.165 | 0.1439205 | 3.767838 | 0 |
| emphasis | 0.0499985 | 26.165 | 0.1294103 | 3.387961 | 0 |
| reordered | 0.0499985 | 26.165 | 0.1438159 | 3.765101 | 0 |

Common target RMS is 0.05; PCM16 quantization yields approximately 0.049998. Reference and diagnostics retain total duration. Pause redistribution preserves the speech sample contents and total silence; reordering preserves complete chunk contents. Their mean/integrated drive is very close to reference but not algebraically identical because 20 ms frame boundaries can combine samples differently. Emphasis and human performance have substantially different mean drive despite equal waveform RMS. The human performance lasts longer and receives more integrated drive. These are measured properties, not hidden nuisance corrections.

The two source performances remain confounded by voice, pacing, microphone/recording characteristics and prior processing. Equal RMS isolates none of those separately. Full-network stochastic dynamics can amplify an input perturbation; a visible late difference need not identify a specific functional circuit. Eight fixed seeds support exploratory characterization, not a population estimate for biological flies. No behavioral output was calibrated. The one-second tail limits any persistence claim.

## Artifacts and reproduction

The comparison page exposes source/processed audio, gain, injected frames, per-seed responses, time traces, observed min–max bands, and corresponding-line navigation. `counts.npz` preserves counts sufficient to recalculate the primary population rates. `raw-artifacts.json` inventories local full-spike archives and hashes; it does not imply those approximately 2.1 GB are served online. Original model provenance and weight/data hashes are in `comparison.json`. See README for run commands and archive keys.

The current apparatus distinguishes some temporal and amplitude-pattern contrasts beyond direct JON injection. It does not establish a stable pooled motor response to these performances. The next experiment should replicate these specified contrasts on held-out seeds and predeclare the temporal metric before considering new sensory mechanics.

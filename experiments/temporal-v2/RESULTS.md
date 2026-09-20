# Temporal confirmation v2 — results

64 completed frozen-connectome simulations: six conditions plus two duration-matched silence controls for each of eight new seeds (101–108). The protocol hash is recorded in every experiment manifest. No weights, neural parameters or auditory encoding rule changed. The observation tail is five seconds.

## Primary downstream temporal test

Values are Hz per neuron except cosine. The criterion was declared before these runs: mean paired trace RMS exceeds pointwise seed-SD RMS, and split-half cosine exceeds 0.5. It is descriptive, not a significance test.

| Comparison | Trace RMS | Variability RMS | Half cosine | Criterion | Whole-audio mean difference |
|---|---:|---:|---:|---|---:|
| human | 0.4929 | 0.2479 | 0.9446 | Met | -0.08913 |
| pauses | 0.3135 | 0.2413 | 0.8578 | Met | +0.00408 |
| reordered | 0.4636 | 0.2413 | 0.9326 | Met | +0.00232 |
| localized | 0.1695 | 0.2148 | 0.6657 | Not met | +0.00108 |
| frame_reverse | 0.3996 | 0.2461 | 0.8978 | Met | +0.01131 |

Redistributed pauses and reordered segments reproduce a temporal distinction in new background conditions while leaving very small whole-audio mean differences. Reversing the exact injected sequence also passes: total dose and the distribution of input values cannot alone explain the temporal trace. This establishes sensitivity to arrangement in this apparatus. A response that follows instantaneous drive can also distinguish these conditions; it does not establish memory or complex temporal computation.

The human/reference comparison passes, but different duration, dose and pacing remain confounded. The common elapsed-time window is not a comparison of corresponding words or lines.

## Local pause and output limits

The single relocated 180 ms pause does not pass the whole-trajectory criterion. Its selected strongest half-second windows all have lower downstream responses in 8/8 seeds, but these windows were selected on this ensemble; they are exploratory, not independent confirmation of a local effect.

At the declared line-6 resumption window, the downstream post-minus-pre contrast differs by +0.05613 Hz/neuron (SD 0.12857), with five positive and three negative paired differences. The aligned injection windows are exactly identical; earlier histories and absolute times differ. This diagnostic does not establish a reliable history-dependent response. Failure of a whole-duration criterion also does not prove that a localized effect is absent.

No comparison passes the pooled descending temporal criterion. The named output circuits are exploratory; their results remain available in the response JSON and page. These measurements do not support a claim of differentiated movement, fear, enjoyment or attention.

## Aftermath and interpretation

Five seconds of aftermath are retained as one-second bins. Signs remain mixed across seeds; some bins lean negative, but these data do not establish a sustained, differentiated aftereffect. Nonzero averages are reported rather than promoted into a narrative of persistence.

Interpretation receives only the saved numerical response summary and timestamps. It distinguishes measurement, functional limits and an affect-theory reading. The strongest episodes are explicitly selected exploratorily. The experiment supports a reading of differently patterned contact with a modeled receiver, while leaving its translation into bodily disposition unresolved.

Every stage selects what can appear: performance becomes waveform; the transducer retains amplitude structure; the model transforms drive into firing; measurements select populations and windows; prose interprets these selections. This layered construction is part of the artwork’s argument, not a claim to unmediated access to animal experience.

## Audit

Raw spikes and full population files remain locally in `results/temporal-v2`. Public `counts.npz` retains per-step global/group counts and all annotated-type phase counts. `confirmation.json` records run provenance, counts hashes, source hashes and per-seed measurements. `raw-artifacts.json` inventories the local raw files. The tests independently reconstruct the reverse-frame trace from the published counts. See README for exact reproduction commands.

Total measured simulation time: 731.4 seconds across 64 runs, excluding setup and analysis.

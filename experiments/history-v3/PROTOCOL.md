# Matched-history experiment v3 — fixed before simulations

Question: does changing earlier auditory input alter the response to a later identical passage, beyond activity that would have continued without that passage?

Keep the original frozen MaleCNS / fly.ai model, parameters, seed/reset procedure, warmup (0.5 s), baseline (1 s), RMS transducer (20 ms), and default one-second observation tail. No training or new biological mechanisms.

Stimulus: use v1's level-matched synthetic PCM. History A is source seconds 0–6. History B is the same three 2-second blocks in reverse block order (4–6, 2–4, 0–2), with samples within blocks unchanged. Probe is source seconds 6–8, identical in every probe condition. These arbitrary clock-aligned cuts are diagnostic edits, not natural alternative performances or linguistic segments. All cuts are on the 20 ms grid. No normalization after editing. Verify equal sample distributions, exact equal injected-value multisets and integrated drive between histories; preserve both PCM and encoding.

Insert gaps of 0, 0.5 and 2 seconds between history and probe. For each gap run A+probe, B+probe, A+quiet, B+quiet. Quiet is two seconds of zeros in the probe slot, not silence throughout the trial. Within each gap all four trials have identical duration and absolute probe-slot onset. Different gaps have different absolute onsets; comparisons across gaps are descriptive, not identical noise at different delays.

New seeds 201–208: eight paired background conditions, not eight biological specimens. Run all twelve conditions for each seed (96 simulations), plus an independently reset duplicate A+probe at zero gap for each seed (8 runs). Total 104. No optional stopping or retrospective sample-size choice. The independent duplicates must match complete spike arrays. Pre-history baseline must match across trials, and each probe/quiet pair must have exactly matching spikes until probe onset. Preserve full local spikes and population counts, compact public counts and provenance.

Primary population: direct JON postsynaptic partners excluding injected cells. Secondary: pooled descending neurons. JO-A/B input check and DNa02, DNp01, MDN, pIP10 are exploratory. No behavior or feeling thresholds.

Compute these within-seed contrasts in the two-second probe slot:
- Total history difference: B+probe minus A+probe.
- Lingering history difference: B+quiet minus A+quiet.
- Probe increment after A: A+probe minus A+quiet.
- Probe increment after B: B+probe minus B+quiet.
- History-dependent probe increment (interaction): (B+probe − B+quiet) − (A+probe − A+quiet).

Compute contrasts from integer spike counts before rate conversion. All probe-slot trials share absolute time and background noise within a seed/gap. The quiet continuations control for unprompted continuation of each history, without assuming linear neural dynamics. The interaction estimates non-additivity at the selected population readout; it is not a decomposition of hidden biological mechanisms.

Primary window: first 0.5 s of the probe slot, five 100 ms bins. Secondary window: full 2 s, twenty bins. For each contrast/window report mean rate difference and paired-seed values/SD/signs, RMS of mean temporal trace, RMS of pointwise sample SD, and cosine between first-four and last-four seed mean traces. Reuse the declared v2 descriptive criterion: temporal mean RMS > temporal SD RMS AND split-half cosine > 0.5. No p-values, significance claims, corrected multiple-test claims or biological population inference. Report every gap, all contrasts and both windows; do not select a gap after seeing results. Scalar sign counts treat <1e-12 Hz/neuron as arithmetic zero.

The interaction is the primary test of changed reception. The two probe increments are manipulation checks. Total and lingering differences distinguish differential response during the probe from residual activity. A failure of the criterion is inconclusive at this sensitivity, not equivalence or proof of pure present-input tracking. Effects at shorter but not longer gaps would support limited-duration dependence for these stimuli, not a fitted memory time constant. No learning, recollection, subjective state or action is inferred.

A downstream rule-based reading receives only numerical criteria, gaps and contrasts, never waveform, poem or reader identity. Distinguish measurement, functional implications and tentative affective interpretation. These statements are about a modeled encounter. The lead-in manipulation changes immediate pre-probe drive as well as earlier sequence; an effect could reflect membrane/spike dynamics or recurrence rather than elaborate memory.

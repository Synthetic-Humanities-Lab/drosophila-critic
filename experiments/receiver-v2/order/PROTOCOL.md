# Equal-drive temporal organization pilot

Declared before runs, 2026-09-22. Original full frozen FlyBrain, original 20 ms
clock, reset/warmup/noise, seeds 1001–1004. Same-duration paired silence.

Source: saved `reference-displacement-1` injection from the provisional receiver
pilot, including its five mechanical-decay input frames. Do not re-encode audio.
This is a diagnostic manipulation at the neural-input boundary, not a new oral
performance or a physiologically calibrated receiver.

Conditions: original order; reverse order of complete 200 ms blocks; fixed random
permutation of those blocks (NumPy default_rng seed 20260922); constant input
at the original mean; silence. Keep any final incomplete block at its original
position. The permutations preserve every injected value, its multiplicity,
mean, total, RMS, capped-frame count and duration exactly (up to summation roundoff).
Keep within-block order. Constant input preserves mean/total/duration only.
Repeat original seed 1001 and require identical spike identities and timing.
21 total runs. No outcome-dependent gain or block-size selection.

Prespecified populations: injected JO-A/B; direct JON postsynaptic partners;
pooled descending neurons. Subtract same-seed silence, then report full-stimulus
mean rate and 1 s tail-rate differences relative to original. Retain native-time
100 ms traces with seed mean/min/max (not confidence bands).

A changed native-time trajectory is expected when input is reordered. For the
stronger temporal-context check, invert each block permutation on the response
before comparing with original: compare identical input blocks in different
preceding contexts. Align at 20 ms, then average into 100 ms bins. This retains
ordinary neural lag and adaptation/recurrent state effects; it does not demonstrate
learning, semantic interpretation, or long-term memory. It also changes alignment
of noise realizations even with paired seeds.

Report RMS of the across-seed mean aligned difference and RMS standard error
(sample SD across four paired differences divided by sqrt(4)); their ratio is
only a descriptive signal/noise diagnostic, not a significance test. Report
leave-one-seed-out cosine similarity of difference trajectories to check whether
a temporal pattern repeats across seeds. Preserve all signs and nulls. Constant
input has no content-block correspondence and receives no realignment analysis.
Do not generate a literary reading or change production receiver behavior.

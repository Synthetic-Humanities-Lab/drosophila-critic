# Matched-history v3 — results

The experiment completed all 104 declared simulations using the original frozen fly.ai / MaleCNS model. Protocol commit: `2e0aba9`, created before the first run. Seeds 201–208 are paired model-background conditions. The lead-ins and probe are acoustic block edits of the existing level-matched synthetic recording.

## Finding

**No changed-reception contrast met the declared criterion**, at any of the three gaps, in either the primary first-half-second window or the secondary full-two-second window. This is a null at the chosen descriptive threshold, not equivalence or proof that the model has no history dependence.

The probe itself is detectable downstream over the full two-second window after both histories at every gap: all six full-window manipulation checks pass. Only two of six first-half-second checks pass. The early window therefore provides a weaker test, and its null must not be overinterpreted.

## Primary changed-reception contrast

Interaction = (B+probe − B+quiet) − (A+probe − A+quiet). Temporal RMS and variability RMS are Hz/neuron; mean difference is the signed first-half-second average. Criterion: temporal mean RMS > seed-SD RMS and split-half cosine >0.5. This rule was fixed before running and is not a statistical significance test.

| Gap (s) | Mean difference | Temporal RMS | Variability RMS | Half cosine | Criterion |
|---:|---:|---:|---:|---:|---|
| 0.0 | -0.01057 | 0.08144 | 0.19815 | 0.54871 | Not met |
| 0.5 | +0.00442 | 0.06055 | 0.18509 | -0.03581 | Not met |
| 2.0 | -0.01450 | 0.05817 | 0.20543 | 0.46326 | Not met |

## Secondary full-window contrast

| Gap (s) | Temporal RMS | Variability RMS | Half cosine | Criterion |
|---:|---:|---:|---:|---|
| 0.0 | 0.13986 | 0.28613 | 0.10614 | Not met |
| 0.5 | 0.07831 | 0.25070 | -0.14824 | Not met |
| 2.0 | 0.10853 | 0.30603 | -0.00173 | Not met |

Neither the total downstream difference during the shared probe nor the lingering difference during quiet continuation meets the criterion in either window at any gap. Pooled descending interactions also fail the criterion throughout. Every group, contrast, time bin and seed remains in `comparison.json`; small named populations are exploratory, not behavior readouts.

## What this permits us to say

Earlier experiments demonstrated that different currently arriving delivery patterns generate repeatable downstream differences. This experiment asks a separate question: whether different preceding sequences change reception of an identical later passage. It does not establish that additional effect for this stimulus pair and readout.

The appropriate affective reading therefore preserves a boundary: differently patterned encounters are measurable, but these measurements do not yet warrant describing the shared passage as received through a reliably altered susceptibility. The model is not shown to learn, remember, feel or act differently. Conversely, a null does not erase its internal dynamical state or exclude effects in other stimuli, populations or finer windows.

## Limits

- One six-second history pair, one two-second probe, eight background seeds, three gaps. This is a bounded apparatus diagnostic, not a general account of fly hearing.
- The first-half-second probe-response checks are inconsistent by the chosen conservative criterion; full-window checks are stronger. We retained the original window and threshold after seeing the data.
- The prior histories differ in their last block as well as earlier order. A positive result could have arisen from ordinary membrane/spike dynamics rather than complex memory.
- Gap comparisons use different absolute probe times and are descriptive. No decay curve or memory time constant can be estimated from these nulls.
- Coarse pooled rates could miss cell-specific or sub-100-ms changes. No exploratory search was substituted for the declared outcome.

## Audit

All eight independent identical-input repeats match their complete spike arrays. All probe/quiet pairs match exactly before probe onset. Baseline spikes match across histories within each seed. Input multisets/dose and common-probe identity are verified. Raw spikes/counts, configuration, upstream/data hashes and frozen weights are checked before analysis. Tests independently reconstruct all three primary-population interaction traces from the public count archive.

Full raw spikes are retained under `results/history-v3`, outside Git. Public `counts.npz` supplies global/group step counts and annotated-type phase counts. The report, strict response-only interpretation input, exact WAVs and encoding JSONs are committed. No poem text or waveform is supplied to the interpreter.

Measured simulation runtime: 433.9 seconds for 104 runs, excluding setup and audit/analysis.

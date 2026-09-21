# Annotated-population screen — results

70 eligible annotated types; 350 type/stanza pairs screened. 12 passed discovery; 5 selected; 2 survived held-out checks.

| Type | Stanza | Total / direct cells | Discovery Δ Hz/neuron | Validation Δ | Survives |
|---|---:|---|---:|---:|---|
| WED163c | 3 | 6 / 4 | -0.1732 | -0.2155 | False |
| CB1038d | 1 | 5 / 5 | -0.2258 | -0.2277 | False |
| SAD021_a | 3 | 6 / 3 | +0.1054 | +0.0399 | False |
| CB4176 | 3 | 7 / 6 | +0.2122 | +0.2026 | True |
| CB1038d | 5 | 5 / 5 | -0.8415 | -0.7949 | True |

Some differences remain localized to annotated populations after all three input-only approximations and repeat across held-out noise runs. CB4176, passage 3: the second recording has a higher firing rate. CB1038d, passage 5: the second recording has a lower firing rate. As an interpretation, delivery distributes disturbance unevenly across the modeled network. These residuals exceed these particular approximations; they do not establish a percept, action, emotion or uniquely connectome-dependent mechanism. The annotations here identify cells and anatomical contact, not an experience.

Whole annotated types are measured, not only their direct-target members. Gates are descriptive and do not control multiple-testing error. Held-out runs repeat the same performances with different simulator noise. This is not independent biological or stimulus validation. Nulls apply to this eligibility rule, stanza-scale measure and comparator set; small circuits and finer temporal patterns are outside the screen. Anatomical membership alone does not establish a sensory percept or action. No new functional association is assigned from a cell-type name.

The full discovery screen, fixed coefficients, validation seed values and nine boundary checks are in discovery.json and comparison.json. Integer count archives have shape seed × stimulus/control × complete 100 ms audio bin × eligible type, in discovery.json eligible order; seeds 64–71 and 101–108 respectively. All inputs and methods remain unchanged.

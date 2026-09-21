# Corresponding performances — retrospective passage analysis

Uses existing original-fly runs; no new simulations. Human boundaries are approximate. All rates below are human minus synthetic, each relative to its matched silence.

| Stanza | Difference Hz/neuron | Seed SD | Positive / negative | Boundary robust | Residual robust: immediate / 0.1s / 0.3s |
|---|---:|---:|---|---|---|
| 1 | -0.0185 | 0.0198 | 1 / 7 | False | False / False / False |
| 2 | -0.0029 | 0.0244 | 3 / 5 | False | False / False / False |
| 3 | +0.0272 | 0.0328 | 6 / 2 | False | False / False / False |
| 4 | -0.1343 | 0.0148 | 0 / 8 | True | True / False / False |
| 5 | -0.0964 | 0.0101 | 0 / 8 | True | False / False / False |

## External input-only baselines

| Smoothing seconds | Fitted gain | Human R² | Human RMSE | Zero-predictor RMSE |
|---|---:|---:|---:|---:|
| 0 | 2.3950 | 0.9110 | 0.1145 | 0.4487 |
| 0.1 | 2.4712 | 0.7616 | 0.1874 | 0.4487 |
| 0.3 | 2.4198 | 0.5038 | 0.2704 | 0.4487 |

The two deliveries distribute the modeled encounter differently across corresponding passages. In passage 4, the downstream firing rate is lower in the second recording. In passage 5, the downstream firing rate is lower in the second recording. This describes a pattern of susceptibility to sound: where a delivery exerts more or less neural disturbance per unit time, without assigning a feeling to it. The second recording also spends longer in these passages. A lower firing rate does not mean a smaller accumulated response.

No passage contrast survives all three input-only approximations and the boundary check. Residual evidence depends on the comparator; this comparison does not isolate a contribution beyond simple amplitude following. No robust pooled descending contrast establishes a differentiated route toward action.

R² describes the ensemble-mean 100 ms trace, not individual fly prediction. Residuals do not isolate connectome causation. Equal RMS does not equal equal dose: the human recording lasts 45.1 s versus 26.17 s and has 10 capped encoder frames. No performance-identity causal claim follows. See PROTOCOL.md and comparison.json for all models, per-seed values and boundary checks.

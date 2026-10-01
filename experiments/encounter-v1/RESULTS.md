# Curated displacement-receiver encounter

32 new full-network simulations; original frozen weights, four paired seeds, three prespecified gains, eight shared silence controls. Nominal gain 1 was fixed before runs.

## Direct auditory recipients

| Gain | Human minus robot, Hz/neuron | Same sign in four seeds |
|---|---:|---|
| 0.5 | -0.034929 | True |
| 1.0 | -0.088332 | True |
| 2.0 | -0.201892 | True |

Passages 2, 4 and 5 retain direction across all seeds, gains and tested ±0.1 s boundary shifts. This is a descriptive robustness check, not a significance test. The human recording also supplies different mean and temporal drive; no emotion or movement is inferred.

Each recording retains its duration and dynamics after linear level matching. Five mechanical decay frames are analyzed as post-sound persistence, followed by three seconds of neural tail.

Simulation/analysis wall time: 573.7 s on the development machine. See result.json for configurations, source hashes and all nominal run hashes. Raw counts and spikes remain locally in results/encounter-v1. All three response reports and nominal injected frames are published.

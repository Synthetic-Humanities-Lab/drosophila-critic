# Provisional receiver sensitivity pilot

Declared before neural runs, 2026-09-22. This is an engineering sensitivity
experiment, not physiological calibration. Production remains rms-jon-v1.

## Evidence boundary

[Clemens et al. 2018](https://www.nature.com/articles/s41467-017-02453-9)
measures compound auditory nerve responses and adaptation. Data/code are available
on request (Data availability). Such signals do not give absolute firing rates
for each MaleCNS neuron or a conversion to FlyBrain voltage.
[Patella and Wilson 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC5952606/)
uses calcium imaging and mechanical stimulation. Its data/software are available
on request; optical responses are not individual spike trains. It supports
heterogeneous tuning, not assigning a guessed tuning curve to each connectome ID.
Lehnert et al. 2013 (doi:10.1016/j.neuron.2012.11.030) is another candidate;
its abstract describes receptor signals accessed through the giant fiber.
Full text was not recovered in this bounded search. No physiological dataset
was imported or fitted. These findings are not a claim that no suitable data exist.

## Adapter and fixed choices

Use the existing Gopfert–Robert representative linear sound-transfer fit, with
48 kHz waveform processing and the existing virtual air calibration. No extra
active amplifier or adaptation stage. Test both displacement and velocity RMS
in 20 ms bins. Scale each by its analytic steady-state response to the SAME
200 Hz digital RMS 0.1 reference, so that this reference would inject 0.4 abstract
voltage at unit strength. This is an engineering anchor, not measured physiology.
Multipliers 0.5, 1, 2; cap 0.8 inherited from flytalk. Report capped frames.
No recording-specific normalization. Final partial frame is zero-padded before
mechanics; retain 100 ms of mechanical decay as extra input frames for ALL arms.
This is followed by the standard 1 second neural tail.

Compare with the unchanged legacy encoder at unit strength. Original full
connectome, original 20 ms neural clock, original noise, reset and warmup.
Preserve frozen weights. Seeds 901–904 are a small pilot, not biological flies.
Equal-duration silence per stimulus; shared across receivers because zero input
is identical. Repeat the 200 Hz unit-displacement input at seed 901 and require
exact spike identities/times. Tones: 200 and 800 Hz, 1 s, digital RMS 0.05,
identical rectangular envelope; test unit-strength arms. Then both archived
level-matched complete poem recordings at all seven arms.

## Measurements and interpretation

For JO-A/B, direct JON postsynaptic partners, and descending neurons: subtract
same-seed, same-duration silence; report mean Hz/neuron during sound and neural
tail; retain native-time 100 ms traces with seed mean and min/max (not confidence
intervals). Compare human minus synthetic mean rates separately for each arm,
report every seed and its sign. Different durations remain different exposures;
whole-recording mean differences are not corresponding-line comparisons.
No population fishing, p-values, significance gates or literary reading.
Tone 800-minus-200 is the controlled frequency contrast. A changed response is
expected from deliberately changed input, not validation of real fly hearing.
An effect with the same sign across seeds and all six mechanical settings is
robust within this limited grid only. Report nulls and reversals equally.

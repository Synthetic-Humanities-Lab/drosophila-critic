# Neural activity to movement, version 1

This is an engineering adapter, not a biological calibration. Its parameters
are fixed before applying either poem's neural recording. The receiver, the
neural timestep, the connectome weights and its noise configuration are unchanged.

The adapter reads **every spike** in seven populations selected by the actual
MaleCNS annotations. It never receives the poem, audio, reader identity, or the
sample of neurons displayed on screen. Rates are absolute spikes/s/cell, smoothed
with an exponential 200 ms time constant. Silence uses exactly the same rules.

- DNg100 supplies forward walking speed: 0.4 cm/s per Hz, capped at 4 cm/s.
- Left minus right DNa02 supplies walking turns: 0.3 rad/s per Hz, capped at 3 rad/s.
- DNp01 requests takeoff when its smoothed rate crosses 2 Hz; it rearms below
  0.5 Hz. A single spike among its two cells can cross this threshold. This is
  an explicit event detector, not a claim that a poem induces fear.
- DLM motor cells supply flight speed: 6 + 2×rate cm/s, capped at 20 cm/s,
  **only after a takeoff request**. Their sustained activity also delays landing.
- Left minus right b1/b2 motor rates supply coarse flight turns: 0.15 rad/s per
  Hz, capped at 3 rad/s. These 20 ms samples cannot recover wingbeat timing.

The associated functions motivate the choice of populations. None of the
publications supplies these gains, speed limits, or transition thresholds.
Zero forward and turn drive holds a standing pose. A turn request starts the
walking policy at a minimum 2 cm/s: this published controller was unstable when
asked to pivot slowly in the combined body. That forward component is a declared
controller requirement, not DNg100 activity or spontaneous roaming.

Initial silence inspection found no DNg100 spikes in the robot-duration seed
1101 silence run, rare DNp01 spikes, and sparse lateral steering spikes. These
facts constrain expectations; they are not a reason to select different cells
after viewing the poems. A quiet or nearly identical movement result remains valid.

The supervisor enforces a minimum 1 second flight, a 4 second takeoff refractory
period, and waits 400 ms below 0.35 Hz DLM activity before requesting landing.
Landing requests are cancelled above 0.75 Hz only before descent starts.
The published walking and flight policies coordinate the actuators. Wing
deployment, touchdown handover, and inward commands at the arena boundary are
our additions. Body feedback goes only to these controllers; it never changes
the frozen nervous system or the imposed sound field.

Sources for the proposed roles: [DNg100](https://pmc.ncbi.nlm.nih.gov/articles/PMC13142387/),
[DNa02](https://pmc.ncbi.nlm.nih.gov/articles/PMC12279373/),
[DNp01](https://www.nature.com/articles/s41586-024-07523-9),
[wing motor control](https://pmc.ncbi.nlm.nih.gov/articles/PMC9750141/).
The anatomy and frozen body controllers come from
[flybody](https://github.com/TuragaLab/flybody), pinned to
`d015e9bfe441bd90ae431bac24c55cb74bdbce26`.

## Body supervision and confinement

The adapter gains above were fixed before the poem runs. Subsequent changes
addressed controller failures shared across inputs, not the direction or size of
poem differences. Walking turns are limited to 1.5 rad/s, with reference speed
and turn acceleration limits of 50 cm/s² and 10 rad/s². `commands` saves both the
supervisor request and the effective body reference after these limits.

A takeoff request near an edge is deferred while the fly walks inward. Within
|x| < 3 cm and |y| < 2 cm, the body spends 0.3 s settling its legs and 0.1 s
deploying its wings; wingbeat commands then ramp in over 0.05 s. The published
wingbeat pattern resets its phase at takeoff; joint positions and velocities
are never reset. Flight references use a 47.5° nose-up pitch and a 2 cm cruise
height. Position-reference error is capped at 0.15 cm, without clamping the
actual body position.

Landing descends at a reference rate of 1.5 cm/s while extending the legs. The
walking policy resumes only after at least two claw sites approach the floor,
MuJoCo detects contact, and thorax height falls below 0.24 cm. Standing smoothly
returns leg actuators to their initial stance targets. These transitions are
engineering additions; they were not supplied as a unified published policy.

Arena steering predicts near-edge motion and turns toward the centre. It starts
inside the physical 20 × 16 × 10 cm bounds to leave braking/turning room. Events
mark the start and end of each intervention, and every 20 ms command sample
records whether confinement was active. There are no invisible positional
resets, root forces, gravity compensation, or frame-rate-dependent physics.

The combined model retains the original leg joints and walking actuator filters
while adding the published flight wing parameters and aerodynamic geoms. The
original flight task omits leg actuation; our combined configuration is an
extension. Physics runs at 50 microseconds in every state because the fast wing
joints remain present on the floor. Policy control intervals are 2 ms walking
and 0.2 ms flight. The anatomy is a female exemplar coupled to a male connectome,
not a registered male whole-animal reconstruction.

## Playback and measurement

Body transforms for all 69 MuJoCo bodies are saved every 20 ms. Their relative
transforms specify articulated joint poses; the renderer interpolates these
poses on the audio clock. It never runs a separate movement simulation.
Flight is measured when thorax height exceeds 0.25 cm and all six claw sites
are clear of the floor, rather than inferred from the supervisor's state name.
Walking distance is horizontal distance while grounded. Turning is cumulative
absolute yaw change, reported in revolutions; it is not a count of discrete
turning behaviours. Totals include the 1.5-second baseline and three-second
post-sound window. The final-distance measure counts horizontal travel after
the recording ends, whether walking or airborne.

These quantities depend on the added body and supervisor as well as the neural
recording. A neural signal can trigger a large nonlinear change in trajectory;
that does not establish a biological effect size. Small floating-point
differences between native and browser physics may accumulate over a long
contact-rich trajectory. Compare paired conditions within one runtime.

## Licenses

The source anatomy is Apache 2.0. The original Figshare policy and wingbeat
datasets are GPL 3.0+, a separate license from the source repository. The
[asset notice](../static/assets/body-v1/NOTICE.txt) identifies the original files,
converted arrays, corresponding export/inference source and license text.

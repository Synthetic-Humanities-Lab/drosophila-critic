# Public encounter — implementation specification

## Reference recorded before implementation

Primary: https://www.instagram.com/reel/Ddgyrj7gqg6/ by highly_unnecessary_,
“Poppy Cartel — EP.2: Cooking on the Fly”. Inspected in the browser on
2026-10-01. The observed frame shows an oblique view along a wooden workbench,
brown anatomical flies with red eyes and transparent wings, concrete vessels,
warm directional lighting and contact shadows. The lower third is a black
brain-and-ventral-nerve-cord display, amber recorded activity and small readouts.
The screenshot in this task records this reference frame. No video assets are
copied or redistributed.

Our composition retains that scene-over-neural-display relationship. A reading
desk faces a fly on a low specimen platform. A human and robot occupy the same
reader position in alternate performances. Camera: fixed oblique perspective;
materials: warm timber, muted green-grey walls, metal robot, warm skin and dark
clothes. No ornamental neural connections. Reader gestures are stage animation;
fly body remains posed, and neural points are actual sampled spikes. Amber
intensity and graph axes are shared between performances.

## Receiver decision fixed before new simulations

Use displacement envelope at nominal gain 1; check gains 0.5 and 2 without
selecting based on poem effects. Source reconstruction: Göpfert & Robert 2002,
Fig. 2C, resonance 394 Hz, Q 1.24, velocity gain 1.13. Existing exact interval-held
linear solver and 200 Hz reference-tone adapter are retained. Literature:
https://doi.org/10.1242/jeb.205.9.1199 . The earlier source audit and numerical
checks are in experiments/receiver-v2/CALIBRATION.md. A single representative
linear fit omits active level-dependent tuning; outside 100–1500 Hz is extrapolation.

Digital RMS 0.1 represents a virtual local particle velocity RMS 0.5 mm/s.
The displacement from a 200 Hz reference maps to 0.4 abstract input voltage;
20 ms envelopes are capped at 0.8 and injected into the existing 138 JO-A/B
targets. This gain is an engineering assumption, not a measured neural current.
There is no added active force model, subtype tuning, semantic encoding or
connectome change. Five frames of mechanical decay follow sound, then three
seconds of neural tail. Analysis marks mechanical decay as post-sound activity.

Biological validation remains limited: numerical tests reconstruct the published
fit, not raw physiological responses or the channel-to-current conversion.
Clemens 2018 and Patella/Wilson 2018 provide relevant adaptation/tuning evidence,
but their underlying datasets are on request and no such data have been fitted.
No outreach is authorized or needed for this release.

## Evidence and presentation

Both original recordings are linearly level-matched with the existing routine.
Run sound and equal-duration silence at seeds 1101–1104, same reset and pinned
FlyBrain. Preserve all raw counts, spikes, encoder frames and hashes locally;
publish aggregate results, numeric interpreter input and a deterministic spatial
sample from seed 1101, explicitly distinguished from four-seed mean traces.
Human boundaries are approximate. Interpretations receive only response JSON.

No paid service, public submission endpoint, new voice generation, or motion
inferred from pooled firing. Existing APIs and historical records stay intact.

# The listening scene

The browser stages a standardized voice being played to a fly. It is a view of
recorded acoustic input and simulated neural activity, not a motor simulation.

## Anatomy

Geometry is derived from [NeuroMechFly / FlyGym](https://github.com/NeLy-EPFL/flygym),
pinned at `38c8ec61034cd59bc5ba0de20688d4a3c0000d60`. Its micro-CT exemplar is
female. MaleCNS supplies a separate male nervous-system dataset. These are not
registered anatomically, not the same animal, and not represented as such.

69 segments use the upstream simplified meshes (up to 2,000 faces per mesh),
rigging offsets/quaternions, neutral-pose angles, and mirrored right-side
geometry. FlyGym's yaw=X, pitch=Y, roll=Z convention is retained. The neutral
pose is baked into a GLB by `scripts/build_fly_asset.py`; there is no MuJoCo
runtime, physical settling, inferred walking, wing motion or motor policy.
Materials, lighting, speaker and camera are authored presentation choices.

The Apache-2.0 license, attribution and a per-source-file hash manifest are in
`static/assets/fly/`. The vendored Three.js 0.180.0 runtime is MIT-licensed.
All display assets load locally. To rebuild the supplied GLB, install
`requirements-assets.txt`, then run `.venv/bin/python scripts/build_fly_asset.py`.

## Exact display mappings

- Speaker-to-fly rings use the saved 20 ms audio RMS: opacity is proportional
  to `min(RMS / 0.2, 1)`. Their position/expansion follows playback time. The wavefront arcs face
  the camera so they remain legible in either view.
  This is a diagram of the input, not a scale model of sound propagation.
- Pedicel/funiculus material emissive intensity is
  `1.4 * min(recorded JO-A/B Hz per neuron / 100, 1)`. This bilateral color
  annotation uses actual group counts; it is not literal neural location,
  measured antenna displacement, or a representation of individual synapses.
- The text beneath the scene is the display-only poem line at the exact
  synthesized line interval. The model and interpreter never receive it.
- Global activity and cell-type values continue to use the original saved
  response; no display values are generated from the poem text.
- The camera can switch between oblique and dorsal views. Camera movement
  changes no measurements. A missing WebGL context/asset displays an explicit
  message; audio and measurements remain available.

## Playback

A custom Web Audio player replaces native HTML media controls, which crashed
the Codex embedded browser in initial testing. `AudioContext.currentTime`
drives the seek control, text, scene and response cursors. Pause freezes the
trajectory. Seeking repositions all displays; replay reuses the saved audio
and response without another simulation. WAV download preserves exact input
PCM. Device output volume/sample-rate conversion can affect what a human
hears, but never changes the waveform that was injected into the fly.

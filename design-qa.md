# Reference scene: layout and playback verification

## Authority and comparison

The user's attached render is the layout target: the third concept at
`output/listening-box-concepts-v2/option-3.png`, 1672 × 941 pixels. The previous
release did not reproduce its composition closely enough. This revision fits
the scene to the supplied image rather than treating it as a general theme.

The running app is captured at 1280 × 720, robot, stanza 2, paused at 5.3 seconds.
The reference and application have the same scene aspect ratio. Their full
pages and scene crops are compared together at a common display scale in
`docs/images/reference-scene-comparison.jpg`. The actual application capture is
`docs/images/reference-scene-desktop.jpg`.

## Changes visible in the comparison

- A long-lens oblique view places the seated reader and open book on the left,
  with a distinct tabletop microphone. A continuous cable reaches the speaker
  on the left wall of the foreground-right glass box.
- The box's size and location follow measured image landmarks. A regression
  check projects seven corners of the unscaled movement volume within 11 pixels
  of their reference positions in the 1073 × 445 scene crop. The book and
  microphone centres are within three pixels of their reference positions.
- The reader's cube head, antenna, bent arms and hands are resized and posed
  around the book. The table edge and legs remain visible. Warm olive materials
  retain the existing scene's visual language.
- The smaller lower-left inset magnifies the same articulated fly against a
  dark background. It fits visible anatomy, including the flight exposure,
  rather than showing a distant fly against a bright floor.
- The wide view retains the actual floor path. The extra overhead map and status
  overlays appear in close, reduced-motion and fallback views, keeping the wide
  scene's layout consistent with the supplied render.
- The full follow view keeps the previously tested camera smoothing and fixed
  viewing direction. Its cutaway now hides surrounding props as well as glass,
  removing stray scenery shadows that crossed the floor during tracking.
- At 390 pixels the inset moves below the hands and book. Scene, neural display
  and sticky playback controls remain available without horizontal overflow.

No simulation result was altered to match the picture. In particular, the fly's
location, articulated pose, wing exposure and floor path at 5.3 seconds come from
the saved recording. They differ from the fly drawn in the illustrative render.
The runtime remains live Three.js geometry, not the mockup used as a backdrop.

## Verification

- The actual reference and running scene were inspected together, including
  separate enlarged scene crops. Desktop and 390 × 844 phone-layout captures
  were inspected in the Codex in-app browser on macOS. This is a responsive
  browser check, not a physical phone/GPU benchmark.
- Robot playback reached 29/29 seconds, and human playback reached 48/48 seconds,
  including the quiet tail. Reader changes use each performance's own stanza
  time: stanza 2 is around 5 seconds for robot and 7 seconds for human.
- End and Home seeking restore the recorded pose and grow/rewind the path.
  Returning to the wide camera restores the table and staged reader. Silence
  has its own trajectory and keeps the reader absent after camera changes.
- Reduced motion disables follow tracking and flashes, removes the inset, and
  keeps the fixed view and path map. Explicit 2D mode retains the recorded path
  and audio controls. Missing-mesh fallback is also checked before publication.
- Automated checks: 173 Python tests, 46 JavaScript tests; Python lint/format,
  modified-file Prettier, public export and whitespace checks. Camera tests
  cover continuous tracking, deterministic seeking, and every recorded joint
  throughout both curated performances. New checks protect the reference
  composition and responsive camera framing.
- Audio, receiver, neural data, body trajectories, local visitor workers and
  upload/recording controls are unchanged. Existing audio, equivalence,
  cancellation and privacy checks remain in the suite. No private recording was
  selected or transmitted for this scene revision.
- Local 15-second recordings of both camera views are saved under
  `output/reference-scene-qa/`. Both measured an 8.3 ms median animation-frame
  interval on this desktop; the 95th percentiles were 9.4 ms (wide) and 9.3 ms
  (follow). These capture timings are not a device-independent guarantee. QA
  pages and experimental archive pages are not part of the public export.

The microphone, cable, speaker, table and reader are theatrical scenery. The
box still represents the same 20 × 16 × 10 cm movement volume and imposed sound
field. The close-up is an optical enlargement; the animal and recorded movement
in the box keep their original scale.

final result: passed

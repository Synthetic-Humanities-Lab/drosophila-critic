# Listening box release: design and playback checks

## Comparison target

Selected visual: `output/listening-box-concepts-v2/option-3.png` (1672 × 941).
The user selected the third **current-build-style** concept, not the earlier
photorealistic set. It retains the existing olive block characters, cream
interface, black neural display, a tabletop glass enclosure, microphone and
wired speaker, and a live fly close-up.

Implementation: `docs/images/listening-box-desktop.jpg` (1280 × 720).
Robot, paused at stanza 2 (5.3 seconds); the mock illustrates approximately
5 seconds. The recorded walking pose and neural counts are used as saved.
CSS viewport: 1280 × 720. Screenshot density: one output pixel per CSS pixel.
The source was normalized to the same width/aspect in a comparison page; no
viewport or density difference is treated as a design defect.

Full-view **and scene-detail** side-by-side evidence:
`docs/images/listening-box-comparison.jpg`. The comparison page includes both
source and rendered screenshot together. Detail views normalize each full page
to 800 pixels wide and select its 515 × 215 scene region.

## Comparison history and fixes

1. **P1: Initial framing clipped the robot and centred it above the box.**
   Evidence: `output/listening-box-qa/iteration-1.jpg`. Changed the table camera,
   reader placement and head proportions while retaining the existing character
   design. The fly and its physical trajectory are unchanged.
2. **P2: The first working composition concealed the table edge and microphone.**
   Evidence: `output/listening-box-qa/comparison.jpg`. Gave the staged reader a
   seated pose, exposed the table edge and legs, and made the microphone stem
   readable. Moved the small path map into unused space at the upper right;
   the lower-left close-up no longer masks the book.
3. **P2: A rear leg could leave the close view during a fast turn.**
   Widened the fixed close camera. A test now projects every articulated joint
   throughout both complete displayed recordings into the narrowest close
   viewport and checks a 10% frame margin.
4. **P2: Camera-button hover lost contrast over the pale floor.**
   Added an opaque hover/focus background. Keyboard focus remains visible.
5. **P2: The enlarged 2D fallback map overlapped its explanatory sentence.**
   Bounded the map vertically, moved the movement state into the unused camera
   control position, and gave the explanation its own space below the map.
   Forced map mode and an intentionally missing GLB both remain usable.

The final comparison and subsequent phone/fallback inspections find no remaining
P0/P1/P2 issue. The reader and speaker are stage props. Their exact pose and
perspective differ from the illustrative mock; the fly's pose is never invented
to match it. The overhead map is retained in addition to the floor path, as
requested. Glass is omitted in the close view so it cannot obstruct the fly at
an enclosure edge.

## Required fidelity surfaces

- **Typography:** existing Georgia heading, Arial body and monospace controls
  preserved; no replacement fonts or new typographic system. Mobile wrapping
  and keyboard focus were inspected.
- **Spacing and layout:** desktop scene/neural split and surrounding interface
  preserved. On mobile the scene remains above the neural display. The box,
  reader, camera control, inset and path map remain in frame.
- **Colours:** existing cream, olive, amber and black interface palette retained;
  warm directional light and readable contact shadows in the scene.
- **Assets:** existing anatomical flybody meshes and articulated transforms;
  existing procedural character design, with a seated reading pose. Live 3D
  geometry is used for the physical scene. No raster mockup or random animation
  replaces measured movement. The actual fly is not enlarged.
- **Copy:** existing poem, voice controls, measurements and recording flow
  retained. Method now explains uniform sound, the staged microphone/speaker,
  cutaway close view and the floor-projected path. No research archive is exported.

## Verification

- Both full curated recordings reach their end (robot 29 s; human 48 s, including
  the quiet tail). The trail remains after playback. Stanza switching uses
  each recording's own clock: stanza 2 is 5.3 s for robot and 7.92 s for human.
- Silence uses its own body trajectory and has zero acoustic input. Pausing,
  replaying and seeking retain synchronized body and path data.
- Fresh browser-local processing of the 26.2-second public robot recording
  completes, produces its own sound and silence body runs, and replays in the
  new scene. This is the public fixture, not a private recording or microphone
  test. Existing upload/record controls and workers are unchanged.
- Reduced motion uses a fixed table view, removes the moving inset and reader
  gestures, and retains the map. 2D mode and a deliberately missing anatomical
  mesh show the recorded path and retain playback controls.
- Desktop and 390-pixel phone layouts inspected in the Codex in-app browser on
  macOS. A phone-sized browser viewport is not a physical phone/GPU test.
- Saved 15-second scene recordings: `output/listening-box-qa/wide.webm`,
  `follow.webm`, `mobile.webm`. Final captures observed an 8.3 ms median animation
  frame interval and approximately 10.1–10.2 ms at the 95th percentile on this
  desktop. These are UI capture timings, not a portable performance guarantee.
- Node checks cover deterministic seeking/frame-rate independence, smooth camera
  tracking, all-joint framing, complete path endpoints and rewind without future
  travel. Existing neural, receiver, audio, body and privacy tests remain in place.
- No neural, receiver, policy, audio or body-recording artifact was changed.
  New runtime modules are included in the public export dependency check.

Saved phone and visitor evidence: `docs/images/listening-box-mobile.jpg`
(390 × 844), `docs/images/listening-box-visitor.jpg`. Test results: **173 Python
and 42 JavaScript tests passed**; Ruff, Python format checks, Prettier and
`git diff --check` passed. Browser console checks found no unexpected errors;
the deliberately missing mesh produces the expected 404 and falls back cleanly.
Capture harnesses and videos under `output/` are local QA artifacts, not part of
the published app. The comparison image preserves the selected visual beside
the implementation without exporting a research/archive page.

## Follow-up polish / limits

The wide scene deliberately shows a small animal; the live inset and enlarged
follow view provide anatomical detail. The box does not add sound attenuation,
reflection, or new physical wall collisions. It depicts the existing bounded
body simulation. Mobile hardware and other browsers need separate device testing.

final result: passed

# Browser release verification — 2026-10-01

The browser report was read from the benchmark page after it completed. Its
full poem spike-count arrays were compared with the original Python nominal
seed-1101 archives, with zero differing timesteps. Voltage/spike fixtures and
independent PCG64 generation also passed; see the saved report and method.

The local visitor flow was exercised in Chromium using the existing public
human WAV through the visible example button. Four complete original-model
runs completed (robot, robot silence, human, human silence). The resulting
mean direct-recipient rates above silence were displayed as 0.272 and 0.193
Hz/neuron respectively. Audio replay, a moving trace cursor, numeric-only
interpretation, cancellation and retry were checked. Reprocessing in-browser
is a separate single-seed comparison, not the curated four-seed statistic.

No private file or live microphone recording was captured in QA. Physical
microphone permission, codec and hardware variation remain untested. Desktop
and mobile-width curated layouts, deployed reader/stanza switching and audio
playback were inspected. Mobile-width inspection is not mobile execution
qualification. Cross-worker peak memory was unavailable.

The public encounter itself does not create a worker or request connectivity.
Only the optional local page's explicit load action requests model chunks.
Neither flow uploads recordings or contacts a processing service.

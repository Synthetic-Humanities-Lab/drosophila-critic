# Comparing performances of one poem

The application accepts two recordings, matches their whole-file RMS with one shared achievable target, and runs the original frozen fly.ai connectome. This is a comparison of acoustic deliveries through a declared receiver, not a ranking of poems or readers.

## Fixed protocol

- Two recordings of the same poem, attested by the submitter. Display text is never passed to the encoder, simulator, or interpretation. There is no transcription or automatic claim that the words match.
- Browser decoding and arithmetic channel averaging produce mono PCM16 WAV. The original compressed file remains on the submitter's computer; its SHA-256 and decoding metadata are recorded. The uploaded waveform and the level-matched waveform are saved separately. Direct API clients supply PCM16 WAV.
- Maximum 120 seconds per recording. Resample to 48 kHz if needed. Apply the existing paired normalization: target RMS is the minimum of 0.05 and both peak-safe achievable levels. One linear gain per recording; no compression or pause removal. Different durations still produce different total exposure.
- The established `rms-jon-v1` encoder measures each 20 ms frame and injects `min(4 × RMS, 0.8)` into the 138 upstream JO-A/B neurons. No frequency tuning or antennal mechanics is claimed. Experimental physical receivers remain separately labelled and are not silently promoted.
- Four seeds, fixed in advance: 1101–1104. Each performance and its equal-duration silence control use the same seeds. Each run resets the original model, uses its existing 0.5 s warmup and 1 s baseline, then records 3 s after sound. Seeds describe simulator variability, not biological flies.
- Primary readout: the connectome's direct JON postsynaptic partners, excluding injected JONs. Secondary readouts: descending neurons and upstream wing motor cells. Injected JONs are an input check. All annotated cell types are an explicitly exploratory screen; the largest changes are selected after measurement.
- Report raw and silence-subtracted rates, paired B-minus-A differences, per-seed direction, 100 ms trajectories and their sample standard deviations, overlap-only temporal separation, and 3 s persistence. Variability bands are descriptive spread across four seeds, not confidence intervals. Timing is elapsed time; different performances are not assumed to align line by line.
- Interpretation receives a strict numeric response summary only. It reports registration, time course and persistence without assigning emotion, comprehension or an overall judgment. An uncertain or zero difference remains an admissible result.

## Operational boundaries

One simulation job at a time. Hosted uploads require a lab access token (`CRITIC_UPLOAD_TOKEN`) and same-origin requests. Tokens stay in page memory. Result URLs are unlisted capability links: anyone with the link can read/download the recording and evidence. Public retention is 24 hours, with deletion on subsequent submissions. Local results persist. Submitted recordings are never automatically copied into the public static replay export.

GitHub Pages cannot run Python or receive recordings. The same frontend runs against the local/API deployment; Pages must state when processing is unavailable. A public compute deployment is a separate completion requirement, not something the static replay can substitute for.

## Completion checks

- [x] Bounded uploads, malformed WAV rejection, token/origin checks, expired artifacts.
- [x] Full original-model run through the API, including a curated Blake pair. Browser replay inspected.
- [ ] Browser file-picker submission: approval review denied the test upload; not bypassed.
- [x] Identical-input paired null and changed-input downstream checks.
- [x] Saved waveform, injection, seeds, raw activity, provenance and text-blind interpretation.
- [x] Usable playback/comparison on desktop and small screens.
- [ ] Verified online compute deployment or explicit outstanding hosting decision.

## Optional corresponding passages

Submissions may supply up to twenty pairs of start/end times, one interval per recording for each corresponding passage. The user identifies the correspondence by listening; the app does not transcribe, embed or interpret the words. Each interval must span at least 0.2 seconds, lie inside its recording, and appear in nonoverlapping chronological order. These annotations never enter the encoder or simulator.

The analyzer snaps each endpoint to the nearest 20 ms frame and measures silence-subtracted rates on each recording's own clock. It also reports interval duration, mean/integrated injected drive and net excess spikes per neuron. It does not stretch neural time to align syllables. Identical injected inputs cannot be compared using different passage cuts: that would introduce a difference entirely through annotation.

A descriptive sensitivity check independently shifts all four endpoints by −0.1, 0 and +0.1 seconds, up to 81 combinations. Bounds are clipped to the recorded frame extent; empty intervals are omitted and the number of valid combinations is reported. “Consistent” requires the same difference direction in every seed under every valid combination. This is not a significance test or validation of the manual alignment. It is a check of whether small timing errors reverse the reported direction. Durations and acoustic structure remain confounded.

The interface shows every supplied passage, with separate A/B playback buttons. Playback stops are scheduled on the audio clock. The interpretation may identify the largest average direct-recipient contrast, explicitly marked as a selection after measurement, and reports whether its direction survives the boundary check. It receives passage numbers and measurements only.

The curated Blake example uses the previously archived five-stanza timing annotations. `whole-result.json` preserves the original whole-recording report; `result.json` adds a reanalysis of the same sixteen saved count archives. `passage_analysis` records source and analysis hashes. The synthetic boundaries derive from synthesis segments; human timings remain approximate. No new simulation was needed for this addition.

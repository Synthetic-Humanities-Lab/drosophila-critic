# Application completion audit — 2026-10-01

The goal remains active. The following is evidence of progress, not a claim of complete online delivery.

| Requirement | Current evidence | Status |
|---|---|---|
| Receive two renditions of the same poem | Multipart comparison API; bounded WAV validation; browser audio conversion and permission attestation | Implemented; actual full Blake pair submitted through API |
| Use the original frozen fly simulation | Sixteen real MaleCNS/flybrain runs in `experiments/performance-v1/result.json`, original source/data hashes and weight checks per run | Verified for published pair |
| Register acoustic delivery differences downstream | Direct JON-recipient rates and temporal traces; paired silence and four fixed seeds; duration/input metrics | Verified on real saved runs; no claim of semantic or subjective response |
| Preserve reproducibility and null results | `VALIDATION.json`: exact repeated activity for four seeds, pulse response above silence; generated diagnostic script retained | Verified |
| Compare corresponding passages | Optional native-clock windows; seed-wise rate/exposure metrics; all supplied passages displayed; ±0.1 s boundary checks | Implemented and applied to the same sixteen recorded runs; whole-recording means reproduced exactly |
| Keep semantics out of simulation and poem out of interpretation | Isolated waveform encoder and strict numeric interpretation schemas; semantic-isolation and invalid-field tests | Verified by code boundaries and focused tests |
| Make response and interpretation inspectable | Separate RESPONSE/READING; downloadable audio, encoding, counts/spikes, provenance and interpretation input | Local API and recorded public example verified |
| Retain scientific modeling seams | `METHOD.md`, receiver research documentation and comparison protocol; experimental physical receiver remains gated | Amplitude apparatus is operational; full physiological hearing is not claimed |
| Public sharing and playback | Lab GitHub repository and Pages; recorded comparisons inspected in browser | Available; final commit's CI/Pages status must be checked after publishing |
| Online processing of new recordings | Docker build and public-mode lab token gate; deployment instructions | **Missing hosting destination/access.** User has been asked which lab account/server to use; no reply yet. Do not provision paid resources without authorization |
| Complete browser file-picker submission | Browser conversion unit tests, API integration, actual API submission, playback and layout checks | **Unverified:** browser approval review denied the upload test. Do not retry or bypass without renewed authorization |

The last two rows are genuine external blockers. Do not create unrelated features to avoid reporting them, and do not mark the full goal complete while they remain unresolved. A connected hosting-account lookup was also denied because this session cannot obtain its required approval. No credentials were exposed and no compute host was provisioned.

Current checks before publication: 136 Python tests and eleven JavaScript tests pass; Ruff and formatting pass. Local passage playback was inspected at its recording-specific time and scheduled end. The public example's original report is preserved as `whole-result.json`; its new passage analysis records source and implementation hashes. No new fly simulation or weight changes were needed for that reanalysis.

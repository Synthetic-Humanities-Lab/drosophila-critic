# Release status — revised scope, October 2026

The user's accepted release is a curated public encounter first, with no paid
compute hosting or submission service. Earlier hosting and upload-test blockers
are not requirements for this release. The old API remains available locally.

- New staged human/robot encounter replaces the landing page; legacy interface
  and deep links remain available through `archive.html`.
- Published antennal displacement reference drives the original 138 JO-A/B
  inputs; no physiology-calibrated neural current is claimed.
- Thirty-two new full frozen-connectome runs: two performances at three
  strengths across four seeds, plus eight shared duration-matched silence runs.
- Spatial samples use nominal seed 1101; traces average four seeds. All visual
  scales are common to the two recordings. Displayed reader motion is theatre.
- Downstream direct-recipient differences retain their direction across tested
  strengths and seeds; passage direction/boundary checks survive for 2, 4 and 5.
- The browser benchmark is separate. Lossless original weights, PCG64 noise and
  original numerical update are tested before any visitor-recording release.
- The original-PCG64 browser benchmark passed on the development desktop: exact
  full-network fixture checks and complete-poem global counts, 40.4 s robot and
  65.1 s human. Optional local recording is available at `listen.html`, with an
  explicit 139 MB download, one paired seed and two matched silence runs.
  Phones are unsupported; other desktop hardware/browser engines are untested.

See `experiments/encounter-v1/` for the new auditable record and
`docs/BROWSER-BENCHMARK.md` for browser reproduction and limitations.

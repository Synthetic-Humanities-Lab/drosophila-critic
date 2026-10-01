# Online editions and deployment

## Public recorded edition

The GitHub Pages website is a clearly labeled replay of Blake's **The Fly**.
It contains the actual fixed-voice WAV, full-connectome neural timeline,
response and interpretation, plus downloadable audit artifacts. It does not
accept new poems or pretend to run a simulator in the browser.

`examples/blake-the-fly/` contains the completed public-domain reading.
`python scripts/export_replay.py` copies that record and the frontend to
`dist/`. Relative asset paths work under the repository's Pages subpath.
The Pages workflow publishes this directory after pushes to `main`.
Only the designated public-domain poem can be exported by this script.
User-submitted poems and local `results/` are excluded from the repository.

## Full interactive edition

A Python container host is required for new poems. The supplied Dockerfile
installs the pinned original fly.ai implementation, connectome and fixed
Kokoro assets. It runs exactly one API process/worker. It does not depend on
the author's computer, a local tunnel, an API key, or browser TTS.

```sh
docker build -t drosophila-critic .
docker run --rm -p 7860:7860 drosophila-critic
```

Local container URL: http://localhost:7860/

On a public host, set:

- `CRITIC_PUBLIC_ORIGIN`: the exact HTTPS origin, without a trailing path,
  e.g. `https://your-assigned-host.example` (replace with the real host).
- `PORT`: assigned HTTP port; defaults to `7860`.
- Optional `CRITIC_RESULTS`: writable ephemeral results directory. Public
  mode defaults to `/tmp/drosophila-critic-results`; no persistent disk needed.

Configure the platform's health check at `/api/health`. One instance only:
job admission is process-local. Start with a CPU container providing at least
4 GB RAM and test peak use under the selected host. Do not choose a 512 MB
static/free web service for this model. Build downloads total about 614 MB,
beyond Python packages. No GPU is required.

Public mode allows only the configured host and same-origin browser POSTs,
limits requests to 20 KB / 2,000 characters / 60 seconds, runs one reading at
a time, and retains at most 20 temporary readings. Readings expire after
24 hours; expired records are removed at the next submission. Storage-full
requests fail explicitly until space expires. Files are accessible to anyone
with the unguessable reading URL; the interface discloses that before use.
Restarting an ephemeral host may erase saved readings sooner. Users should
download results they want to keep. This is a small shared prototype, not a
multi-user service with accounts or guaranteed retention.

No hosting subscription or paid resources have been created. Choose the
lab's hosting account and spending limit before provisioning that service.
The recorded edition and public source can be shared independently meanwhile.

## Lab performance uploads

The same container now serves `/performances.html` and `POST /api/comparisons`. Set `CRITIC_UPLOAD_TOKEN` to a strong secret via the hosting platform's secret store; never commit it or put it in a URL. Public-mode uploads are disabled without it. The page asks for the token and retains it in memory only. POST requires `Authorization: Bearer …` and same-origin access. Do not enable anonymous submissions.

Multipart fields: files `a`, `b` (PCM16 WAV, mono/stereo, 8–96 kHz, 1–120 seconds, at most 12 MB each) and `metadata` JSON containing `poem`, `label_a`, `label_b`, `same_poem_attested: true`. The browser supports other formats by decoding locally to mono 48 kHz WAV. Browser-decode provenance fields `source_sha256_a/b` and `source_format_a/b` are optional, submitter-reported metadata; the server independently hashes the uploaded WAVs.

Each comparison runs four shared seeds, each with both recordings and each recording's duration-matched silence control (16 runs). Tail recording lasts three seconds. All work shares the existing single-worker admission lock. The POST body is streamed into a bounded buffer (24,020,000 bytes maximum); the original text-only endpoint retains its 20 KB limit. Limit reverse-proxy bodies consistently. Allow long-running CPU work; HTTP submission itself returns immediately with a job ID.

Raw spike data is substantial. Public comparison admission reserves 4 GB of available disk and checks that existing result files plus the reservation fit a 10 GB storage budget. This is a conservative preflight, not an OS filesystem quota. Use a volume quota/host limit for a hard boundary. Public links expire after 24 hours and files are pruned on subsequent submissions. This applies to original recordings too. Local mode retains files indefinitely.

Recording links are unlisted, **not authenticated private storage**: anyone with a result URL can access its recordings and measurements. The UI discloses this. For sensitive recordings use a private network or add authenticated artifact access before use. The static export copies only `experiments/performance-v1`, the deliberately curated Blake example; it never copies `results/`.

A public processing host is still unprovisioned. GitHub Pages publication does not satisfy that deployment requirement.

Optional `metadata.passages` is an ordered array of at most twenty objects shaped as `{"a":{"start":0.0,"end":4.9},"b":{"start":1.2,"end":7.8}}`, with seconds on each recording's own clock. These are analysis annotations, not inputs to the fly. The metadata field is limited to 16 KiB; all existing total-body, waveform, token and retention limits still apply.

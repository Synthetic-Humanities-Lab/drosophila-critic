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

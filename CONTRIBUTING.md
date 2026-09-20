# Working on the instrument

Start with README.md, METHOD.md and docs/AUDITORY_ENTRY.md. Clone this lab
repository, make a branch, and open a pull request. The source, exact voice
setup, simulator pin, public Blake record and Docker deployment are included.
Large models/connectome data are downloaded by setup rather than committed.

Keep these boundaries intact:

1. Only audio-derived frames reach the unchanged flybrain simulation.
2. The connectome is frozen; no learned policy/readout is introduced.
3. The interpreter receives only its strict response summary, never the poem.
4. The 3D body is illustrative anatomy; motor behavior cannot be invented
   from aggregate neural activity.
5. New modeling choices belong in METHOD.md, with provenance in results.

Run `python -m pytest -q`, Ruff check/format, and
`node --test tests/audio-player.test.mjs`. The fixed-voice integration test
requires `python scripts/setup_voice.py`. Full connectome validation is
`python scripts/validate.py` after downloading the data.

Changes to the voice, transducer or simulator settings require a new recorded
edition and new evidence. Never relabel old audio or neural data as a new run.

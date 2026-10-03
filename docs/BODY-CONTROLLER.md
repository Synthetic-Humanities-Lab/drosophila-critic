# Body-controller decision — 2 October 2026

**Decision: retain measured neural/antenna playback; do not ship inferred walking.**
The published walking controller runs and passes its command checks. What is
missing is a qualified neural-to-command mapping and a measured browser runtime.
The controller itself is not a failure, and the auditory response is not zero.

## Controller actually inspected and executed

[TuragaLab/flybody](https://github.com/TuragaLab/flybody), commit
`d015e9bfe441bd90ae431bac24c55cb74bdbce26`, Apache-2.0. The official
[2025 paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12310536/) describes a
MuJoCo body and pretrained locomotion policies. Its low-level controller has a
functional role analogous to motor circuitry; it is not an exact reconstruction
of the fly’s nerve cord.

We downloaded the authors’ [trained policies](https://ndownloader.figshare.com/files/44815195)
from their official repository’s download list. Archive: 6,537,720 bytes,
SHA256 `2d9937c9af2baafad1690c1b318791bde417b4d26dd96d4385ab6723d5d58582`.
The walking SavedModel hash and runtime versions are in
[`command-test.json`](../experiments/body-controller-v1/command-test.json).
No training or checkpoint modification occurred. Checkpoints and the optional
Python environment remain outside Git and are not loaded by the website.

The walking policy accepts proprioceptive/body observations and 65 samples of
future desired displacement and orientation. It outputs 59 actuator commands
at a 2 ms control interval. The supplied trajectory helper uses cm/s and rad/s;
none of these inputs is a connectome spike count. Its body feedback loop stays
inside the policy/MuJoCo simulation. It does not feed back into our frozen brain.

## Command test

Before running, the diagnostic required 600 finite steps (1.2 s), no early
termination, and tracking error below the upstream 0.3 cm termination distance.
The repeated forward trajectory had to be exactly identical. These are software
and command-following checks, not physiological validation.

| Command | Maximum position error | Wall time including environment setup | Outcome |
| --- | ---: | ---: | --- |
| Stand | 0.0317 cm | 7.92 s | pass |
| Forward at 2 cm/s | 0.0357 cm | 6.55 s | pass |
| Forward with 2 rad/s turning | 0.0303 cm | 7.00 s | pass |
| Repeated forward | 0.0357 cm | 7.10 s | exact repeat |

The isolated Mac environment uses TensorFlow 2.16.2 / TFP 0.24 rather than the
upstream Linux-oriented TF 2.8 stack. TFP’s public composite-tensor decorator
registers the type names stored by the older checkpoint. That compatibility
step changes deserialization, not policy weights. Headless `MUJOCO_GL=disable`
is required here; importing the default GLFW backend hung in the sandbox.
These environment differences are a limitation of this local replication.

Reproduce from the repository root after obtaining the official source and
checkpoint in the paths below:

```sh
python3.12 -m venv vendor/flybody/.venv
PIP_CACHE_DIR=/tmp/drosophila-pip-cache vendor/flybody/.venv/bin/python -m pip install -e vendor/flybody 'tensorflow==2.16.2' 'tensorflow-probability==0.24.0' 'tf-keras==2.16.0' 'dm-control==1.0.47' 'mujoco==3.14.0'
MUJOCO_GL=disable MPLBACKEND=Agg MPLCONFIGDIR=/tmp/drosophila-mpl vendor/flybody/.venv/bin/python scripts/check_body_controller.py --policy results/body-controller/policies/walking --output experiments/body-controller-v1/command-test.json
PYTHONPATH=. .venv/bin/python scripts/audit_body_outputs.py
```

## Why the poem does not yet command that body

DNa02 is a defensible steering candidate: published work relates bilateral
activity differences to turning during walking ([Rayshubskiy et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC12279373/)).
That association does not supply a calibrated conversion from this model’s
20 ms LIF spikes to rad/s, choose a baseline walking state, or establish the
correct temporal filter. Converting pooled activity into speed would bypass
precisely the missing connection.

We inspected the saved nominal poem/silence pairs at seeds 1101–1104, including
DNa02 separately by annotated side, MDN, DNg100 and DNp01. The
[complete audit](../experiments/body-controller-v1/poem-output-audit.json)
retains body IDs, raw mean rates, changes and changed-timestep counts. Mean
DNa02 left-minus-right changes span −0.115 to +0.038 spikes/s for the robot,
and −0.200 to +0.022 for the human. Directions vary across seeds. Other
candidate mean changes are also small; individual spike timings can differ.
This is not evidence of a reproducible turning command, nor proof that the
receiver has no temporal effect.

No arbitrary multiplier was selected to make these differences walk. No
motor-pathway-to-body positive control was run because that mapping has not
been specified or qualified. Successful manual commands to flybody do not count
as a neural coupling test. The next scientific step is to preregister one
lateralized steering adapter from published spike/turn measurements, test its
motor-pathway positive control and silence first, and only then apply poem runs.
Its engineering units and assumptions would need to be explicit.

Upstream fly.ai’s browser world is not a ready substitute. Its small fly
network is constructed; its full-connectome export quantizes weights and uses
other settings. Its own full-connectome notes report a weak descending-to-VNC
motor relay and failed attempted gain adjustments. Those results concern its
configuration, not a new positive control performed on ours. We preserve our
weights and noise instead of importing those modifications.

## Browser feasibility

The selected controller is Python/TensorFlow/MuJoCo, with native body assets
and simulation dependencies; no equivalent worker implementation comes with
this repository. The measured local 1.2 s commands took 6.55–7.92 s including
setup. This is not a browser timing or proof that optimization cannot work.
A browser policy/physics port, equivalence check, memory measurement and
cancellation test remain required. Shipping a saved curated walk would not
supply body responses to arbitrary visitor audio.

The public release therefore completes visitor **neural** replay while keeping
body movement explicitly unavailable. Its antenna colour and neural display
are measured/model-derived; the reader’s gestures remain theatre.

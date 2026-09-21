"""Two-stage screen on archived original simulations, with frozen discovery selection."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from critic.passages import bins, fit_gain, smooth_drive
from critic.population_screen import evidence, select_candidates, survives

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/populations-v6"
TAUS = [0, 0.1, 0.3]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, allow_nan=False, separators=(",", ":")))


def anatomy():
    inventory = read(ROOT / "docs/population-inventory.json")
    for name, expected in inventory["data_sha256"].items():
        if sha(ROOT / "data" / name) != expected:
            raise ValueError("Connectome archive changed")
    with np.load(ROOT / "data/brain.npz") as p:
        types, ids = p["cell_type"], p["ids"]
    ears = np.flatnonzero(np.isin(ids, inventory["jon_body_ids"]))
    if len(ears) != 138:
        raise ValueError("Injected identity mismatch")
    from scipy import sparse

    weights = sparse.load_npz(ROOT / "data/weights.npz").tocsc()
    indices, indptr = weights.indices, weights.indptr
    targets = np.setdiff1d(
        np.unique(np.concatenate([indices[indptr[i] : indptr[i + 1]] for i in ears])), ears
    )
    if len(targets) != 1017:
        raise ValueError("Direct-target inventory mismatch")
    names, sizes = np.unique(types, return_counts=True)
    return [
        dict(type=str(n), total=int(size), direct=int(np.sum(types[targets] == n)))
        for n, size in zip(names, sizes)
        if str(n).strip()
        and "," not in str(n)
        and size >= 5
        and np.sum(types[targets] == n) >= 3
        and n not in types[ears]
    ]


def extract(edition, seeds, eligible):
    public = ROOT / "experiments" / edition
    manifest = read(public / "manifest.json")
    inventory = read(ROOT / "docs/population-inventory.json")
    data, artifacts = {}, {}
    configuration = None
    for name in ["reference", "human"]:
        n = manifest["conditions"][name]["frames"]
        arrays = []
        for seed in seeds:
            pair = []
            for label in [name, f"silence-{n}"]:
                folder = ROOT / "results" / edition / f"{label}-{seed}"
                meta = read(folder / "run.json")
                file = folder / "populations.npz"
                if sha(file) != meta.get("counts_sha256", meta.get("populations_sha256")):
                    raise ValueError("Source counts changed")
                fly = meta["fly"]
                if (
                    not fly["weights_unchanged"]
                    or fly["seed"] != seed
                    or fly["data_sha256"] != inventory["data_sha256"]
                ):
                    raise ValueError("Simulator provenance mismatch")
                signature = {
                    k: fly[k]
                    for k in [
                        "configuration",
                        "runtime_weights_sha256",
                        "source_sha256",
                        "timestep",
                    ]
                }
                if configuration is None:
                    configuration = signature
                if signature != configuration:
                    raise ValueError("Neural parameters changed between paired runs")
                artifacts[str(file.relative_to(ROOT))] = dict(sha256=sha(file), metadata=meta)
                with np.load(file) as p:
                    if (
                        int(p["bin_steps"]) != 5
                        or float(p["dt"]) != 0.02
                        or np.flatnonzero(p["phase"] == "audio")[0] != 75
                    ):
                        raise ValueError("Unexpected archived clock")
                    indexes = [list(p["type_names"]).index(e["type"]) for e in eligible]
                    if list(p["type_sizes"][indexes]) != [e["total"] for e in eligible]:
                        raise ValueError("Population size mismatch")
                    pair.append(p["bin_counts"][15 : 15 + n // 5, indexes].astype(np.int64))
            arrays.append(np.stack(pair))
        data[name] = np.stack(arrays)  # seed, stimulus/control, time, type
    return data, artifacts, configuration


def windows(manifest, stanza):
    first = [1, 6, 11, 16, 21][stanza - 1]
    result = {}
    for name in ["reference", "human"]:
        lines = {r["line"]: r for r in manifest["conditions"][name]["lines"]}
        result[name] = [lines[first]["start"], lines[first + 3]["end"]]
    return result


def inputs():
    drive = {}
    manifest = read(ROOT / "experiments/delivery-v1/manifest.json")
    for name in ["reference", "human"]:
        one = read(ROOT / f"experiments/delivery-v1/{name}/encoding.json")
        two = read(ROOT / f"experiments/temporal-v2/{name}-encoding.json")
        if one != two:
            raise ValueError("Performances differ between ensembles")
        if (
            sha(ROOT / f"experiments/delivery-v1/{name}/encoding.json")
            != manifest["conditions"][name]["encoding_sha256"]
        ):
            raise ValueError("Encoding changed")
        drive[name] = np.array([f["injected_voltage"] for f in one])
    return drive, manifest


def make_predictions(drive, gains):
    return {
        k: {n: g * smooth_drive(x, float(k)) for n, x in drive.items()} for k, g in gains.items()
    }


def discover():
    eligible = anatomy()
    data, artifacts, configuration = extract("delivery-v1", range(64, 72), eligible)
    drive, manifest = inputs()
    sizes = np.array([e["total"] for e in eligible])
    rates = {n: (d[:, 0] - d[:, 1]) / (0.1 * sizes) for n, d in data.items()}
    rows = []
    for j, e in enumerate(eligible):
        # fit_gain accepts 20 ms samples; repeat each measured bin to preserve its mean.
        gains = {
            str(t): fit_gain(
                drive["reference"][: rates["reference"].shape[1] * 5],
                np.repeat(rates["reference"][:, :, j], 5, axis=1),
                t,
            )
            for t in TAUS
        }
        pred = {
            k: {n: bins(v) for n, v in pair.items()}
            for k, pair in make_predictions(drive, gains).items()
        }
        for stanza in range(1, 6):
            ev = evidence(
                rates["reference"][:, :, j],
                rates["human"][:, :, j],
                windows(manifest, stanza),
                pred,
            )
            rows.append(dict(**e, stanza=stanza, gains=gains, evidence=ev))
    selected = select_candidates(rows)
    payload = dict(
        protocol_sha256=sha(OUT / "PROTOCOL.md"),
        eligible=eligible,
        screen=rows,
        selected=selected,
        artifacts=artifacts,
        configuration=configuration,
        discovery_seeds=list(range(64, 72)),
    )
    save(OUT / "discovery.json", payload)
    np.savez_compressed(OUT / "discovery-counts.npz", **data)
    print(
        f"{len(eligible)} eligible types, {len(rows)} pairs, {sum(r['evidence']['qualifies'] for r in rows)} qualified; {len(selected)} selected",
        flush=True,
    )
    for r in selected:
        print(r["type"], r["stanza"], r["evidence"]["raw"][4]["mean"], flush=True)


def validate():
    discovery = read(OUT / "discovery.json")
    if discovery["protocol_sha256"] != sha(OUT / "PROTOCOL.md"):
        raise ValueError("Protocol changed after selection")
    eligible = discovery["eligible"]
    data, artifacts, configuration = extract("temporal-v2", range(101, 109), eligible)
    if configuration != discovery["configuration"]:
        raise ValueError("Validation model differs from discovery")
    drive, manifest = inputs()
    sizes = np.array([e["total"] for e in eligible])
    rates = {n: (d[:, 0] - d[:, 1]) / (0.1 * sizes) for n, d in data.items()}
    results = []
    for candidate in discovery["selected"]:
        j = next(i for i, e in enumerate(eligible) if e["type"] == candidate["type"])
        pred = {
            k: {n: bins(v) for n, v in pair.items()}
            for k, pair in make_predictions(drive, candidate["gains"]).items()
        }
        ev = evidence(
            rates["reference"][:, :, j],
            rates["human"][:, :, j],
            windows(manifest, candidate["stanza"]),
            pred,
        )
        results.append(
            dict(
                type=candidate["type"],
                stanza=candidate["stanza"],
                total=candidate["total"],
                direct=candidate["direct"],
                gains=candidate["gains"],
                discovery=candidate["evidence"],
                validation=ev,
                survives=survives(candidate["evidence"], ev),
            )
        )
    np.savez_compressed(OUT / "validation-counts.npz", **data)
    summary = dict(
        candidates=[
            dict(
                population=r["type"],
                passage=r["stanza"],
                difference=r["validation"]["raw"][4]["mean"],
                survives=r["survives"],
            )
            for r in results
        ]
    )
    # Template sees this numerical response representation only.
    from critic.population_reading import ReadingInput, interpret

    reading = interpret(ReadingInput(**summary))
    result = dict(
        eligible_count=len(eligible),
        screened_pairs=len(discovery["screen"]),
        qualified_discovery=sum(r["evidence"]["qualifies"] for r in discovery["screen"]),
        candidates=results,
        reading=reading,
        artifacts=artifacts,
        discovery_sha256=sha(OUT / "discovery.json"),
        counts_sha256={n: sha(OUT / n) for n in ["discovery-counts.npz", "validation-counts.npz"]},
        analysis_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                Path(__file__),
                ROOT / "critic/population_screen.py",
                ROOT / "critic/population_reading.py",
            ]
        },
    )
    save(OUT / "comparison.json", result)
    save(OUT / "interpretation-input.json", summary)
    lines = [
        "# Annotated-population screen — results\n",
        f"{len(eligible)} eligible annotated types; {len(discovery['screen'])} type/stanza pairs screened. {result['qualified_discovery']} passed discovery; {len(results)} selected; {sum(r['survives'] for r in results)} survived held-out checks.\n",
        "| Type | Stanza | Total / direct cells | Discovery Δ Hz/neuron | Validation Δ | Survives |",
        "|---|---:|---|---:|---:|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['type']} | {r['stanza']} | {r['total']} / {r['direct']} | {r['discovery']['raw'][4]['mean']:+.4f} | {r['validation']['raw'][4]['mean']:+.4f} | {r['survives']} |"
        )
    lines += [
        "\n" + reading,
        "\nWhole annotated types are measured, not only their direct-target members. Gates are descriptive and do not control multiple-testing error. Held-out runs repeat the same performances with different simulator noise. This is not independent biological or stimulus validation. Nulls apply to this eligibility rule, stanza-scale measure and comparator set; small circuits and finer temporal patterns are outside the screen. Anatomical membership alone does not establish a sensory percept or action. No new functional association is assigned from a cell-type name.",
        "\nThe full discovery screen, fixed coefficients, validation seed values and nine boundary checks are in discovery.json and comparison.json. Integer count archives have shape seed × stimulus/control × complete 100 ms audio bin × eligible type, in discovery.json eligible order; seeds 64–71 and 101–108 respectively. All inputs and methods remain unchanged.",
    ]
    (OUT / "RESULTS.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["discover", "validate"])
    args = parser.parse_args()
    discover() if args.stage == "discover" else validate()

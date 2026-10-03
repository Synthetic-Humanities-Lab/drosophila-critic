"""Run the predefined four paired seeds; every failure remains in the report."""

import concurrent.futures
import json
import os
import subprocess
import sys
from pathlib import Path


def case(args):
    reader, condition, seed = args
    path = Path(f"results/body-controller/trajectories/{reader}-{condition}-{seed}.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "scripts/run_body_trajectories.py",
        "--reader",
        reader,
        "--condition",
        condition,
        "--seed",
        str(seed),
    ]
    with path.open("w") as log:
        result = subprocess.run(
            command, stdout=log, stderr=subprocess.STDOUT, env=os.environ.copy()
        )
    record = {
        "reader": reader,
        "condition": condition,
        "seed": seed,
        "exit_code": result.returncode,
        "log": str(path),
    }
    print(record, flush=True)
    return record


if __name__ == "__main__":
    cases = [
        (a, c, s)
        for a in ["a", "b"]
        for c in ["sound", "silence"]
        for s in [1101, 1102, 1103, 1104]
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(case, cases))
    Path("results/body-controller/batch-report.json").write_text(json.dumps(result, indent=2))
    if any(r["exit_code"] for r in result):
        sys.exit(1)

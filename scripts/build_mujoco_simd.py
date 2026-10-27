"""Build the pinned MuJoCo engine with strict SIMD; never patch its physics source."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

COMMIT = "9ecbb9d7b5ee623f54745638d36799ff90e6f7cd"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    source = args.source.resolve()
    revision = subprocess.check_output(["git", "-C", source, "rev-parse", "HEAD"], text=True)
    if revision.strip() != COMMIT:
        parser.error("The source checkout must be the pinned MuJoCo 3.14.0 commit.")
    version = subprocess.check_output(["emcc", "--version"], text=True)
    if "4.0.10" not in version.splitlines()[0]:
        parser.error("Use Emscripten 4.0.10 for this build.")
    changed = subprocess.check_output(
        ["git", "-C", source, "diff", "--name-only", "HEAD"], text=True
    )
    if set(changed.splitlines()) - {"wasm/CMakeLists.txt"}:
        parser.error("The MuJoCo source has unrelated changes.")
    extra = subprocess.check_output(
        [
            "git",
            "-C",
            source,
            "ls-files",
            "--others",
            "--exclude-standard",
            "wasm/codegen/generated",
        ],
        text=True,
    )
    if extra.strip():
        parser.error("Unexpected untracked binding sources; use a clean checkout.")
    # Debug information disables some of Emscripten's ordinary post-link passes.
    # Keep upstream assertions, exceptions, memory growth and all physics options.
    original = subprocess.check_output(
        ["git", "-C", source, "show", "HEAD:wasm/CMakeLists.txt"], text=True
    )
    cmake_file = source / "wasm/CMakeLists.txt"
    optimized = original.replace('    "-gsource-map"\n', "").replace('    "-g"\n', "")
    if cmake_file.read_text() not in [original, optimized]:
        parser.error("Unexpected changes to the upstream WASM build configuration.")
    cmake_file.write_text(optimized)
    prefixes = {str(source)}
    # CMake canonicalizes macOS /private/tmp to /tmp in generated compile commands.
    if str(source).startswith("/private/"):
        prefixes.add(str(source).removeprefix("/private"))
    flags = "-msimd128 -ffp-contract=off " + " ".join(
        f"-ffile-prefix-map={prefix}=mujoco" for prefix in sorted(prefixes)
    )
    subprocess.run(
        [
            "emcmake",
            "cmake",
            "-S",
            str(source),
            "-B",
            str(args.build),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DMUJOCO_WASM_THREADS=OFF",
            "-DMUJOCO_BUILD_TESTS_WASM=OFF",
            f"-DCMAKE_C_FLAGS={flags}",
            f"-DCMAKE_CXX_FLAGS={flags}",
        ],
        check=True,
    )
    subprocess.run(["cmake", "--build", str(args.build), "-j", str(args.jobs)], check=True)
    args.output.mkdir(parents=True, exist_ok=True)
    digests = {}
    for name in ["mujoco.js", "mujoco.wasm"]:
        target = args.output / name
        shutil.copyfile(source / "wasm/dist" / name, target)
        data = target.read_bytes()
        digests[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    print(json.dumps({"source_commit": COMMIT, "files": digests}, indent=2))


if __name__ == "__main__":
    main()

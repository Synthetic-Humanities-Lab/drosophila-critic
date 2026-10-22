"""Publish the listening app and its evidence; keep development pages offline."""

import argparse
import hashlib
import re
import shutil
import tempfile
from pathlib import Path

if __package__:
    from .pack_playback import optimize_playback
else:
    from pack_playback import optimize_playback

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = (
    "index.html",
    "listen.html",
    "encounter.css",
    "encounter.js",
    "encounter-data.js",
    "arena-scene.js",
    "follow-camera.js",
    "listening-room.js",
    "recorded-path.js",
    "body-view.js",
    "body-recording.js",
    "parallel-load.js",
    "neural-scene.js",
    "audio-player.js",
    "playback-data.js",
    "recording-panel.js",
    "local-audio.js",
    "local-session.js",
    "content-hash.js",
    "simulation-contract.js",
    "silence-control.js",
    "result-store.js",
    "worker-session.js",
    "browser-benchmark.worker.js",
    "browser-brain.js",
    "browser-random.js",
    "neural-capture.js",
    "body-session.js",
    "body.worker.js",
    "body-policy.js",
    "body-adapter.js",
    "body-runtime.js",
    "body-processing.js",
    "body-metrics.js",
    "body-dense.wasm",
)
PUBLIC_DIRECTORIES = ("assets", "vendor", "browser-model-v1")
PLAYBACK_DIRECTORIES = ("encounter-v1", "encounter-v2", "encounter-v3")


def preload_interface(output: Path):
    """Start the actual entry module's static dependencies without serial discovery."""
    seen = set()

    def visit(path):
        for dependency in re.findall(
            r'(?:^|\n)\s*(?:import|export)\s+[^;]*?\bfrom\s*["\'](\.[^"\']+\.js)["\']',
            path.read_text(),
        ):
            target = (path.parent / dependency).resolve()
            if not target.is_relative_to(output.resolve()) or not target.is_file():
                raise ValueError(f"Missing interface dependency: {dependency}")
            relative = target.relative_to(output.resolve()).as_posix()
            if relative not in seen:
                seen.add(relative)
                visit(target)

    visit(output / "encounter.js")
    links = "\n".join(f'<link rel="modulepreload" href="./{name}" />' for name in sorted(seen))
    links += '\n<link rel="preload" as="fetch" crossorigin href="./experiments/encounter-v4/manifest.json" />'
    page = output / "index.html"
    page.write_text(
        page.read_text().replace('<script type="module"', links + '\n<script type="module"', 1)
    )


def version_interface(output: Path):
    """Give each published interface an immutable set of module/style URLs."""
    files = sorted(
        path
        for path in [*output.glob("*.js"), *output.glob("*.css")]
        if not re.search(r"\.[0-9a-f]{16}\.", path.name)
    )
    digest = hashlib.sha256((output / "index.html").read_bytes())
    for path in files:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    version = digest.hexdigest()[:16]
    names = {path.name: f"{path.stem}.{version}{path.suffix}" for path in files}
    for path in [*output.glob("*.html"), *files]:
        text = path.read_text()
        for old, new in names.items():
            text = text.replace(f"./{old}", f"./{new}")
        target = output / names.get(path.name, path.name)
        target.write_text(text)
    return version


def export(output: Path):
    output = output.resolve()
    if output == ROOT or ROOT.is_relative_to(output) or output.is_relative_to(ROOT / "static"):
        raise ValueError("Export requires a separate generated output directory")
    if output.exists() and not (
        (output / ".nojekyll").is_file()
        and (output / "index.html").is_file()
        and "The Drosophila Critic" in (output / "index.html").read_text()
    ):
        raise ValueError("Refusing to replace a directory that is not a generated replay export")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Finish the new edition before replacing the old generated bundle. Rebuilding
    # removes retired pages and stale hashed modules, including on local exports.
    with tempfile.TemporaryDirectory(prefix=".replay-export-", dir=output.parent) as temporary:
        staged = Path(temporary) / "site"
        staged.mkdir()
        for name in PUBLIC_FILES:
            shutil.copy2(ROOT / "static" / name, staged / name)
        for name in PUBLIC_DIRECTORIES:
            shutil.copytree(ROOT / "static" / name, staged / name)
        for name in PLAYBACK_DIRECTORIES:
            shutil.copytree(ROOT / "experiments" / name, staged / "experiments" / name)
        optimize_playback(staged)
        preload_interface(staged)
        version_interface(staged)
        (staged / ".nojekyll").touch()
        if output.exists():
            shutil.rmtree(output)
        staged.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    export(args.output)

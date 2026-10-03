import re
from pathlib import Path

import pytest

from scripts import export_replay

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_module_dependencies_are_in_public_bundle():
    files = set(export_replay.PUBLIC_FILES)
    for name in files:
        if not name.endswith((".html", ".js")):
            continue
        text = (ROOT / "static" / name).read_text()
        for dependency in re.findall(r'["\']\./([^"\']+\.(?:js|css|wasm))["\']', text):
            assert (
                dependency in files or dependency.split("/")[0] in export_replay.PUBLIC_DIRECTORIES
            ), (name, dependency)
    assert {name for name in files if name.endswith(".html")} == {"index.html", "listen.html"}


def test_reexport_removes_retired_pages_and_data_but_keeps_source(tmp_path, monkeypatch):
    source = tmp_path / "source"
    static = source / "static"
    static.mkdir(parents=True)
    for name in export_replay.PUBLIC_FILES:
        (static / name).write_text("The Drosophila Critic" if name == "index.html" else "fixture")
    (static / "archive.html").write_text("Historical research")
    for name in export_replay.PUBLIC_DIRECTORIES:
        (static / name).mkdir()
        (static / name / "asset.txt").write_text("fixture")
    for name in export_replay.PLAYBACK_DIRECTORIES:
        folder = source / "experiments" / name
        folder.mkdir(parents=True)
        (folder / "manifest.json").write_text("{}")
    monkeypatch.setattr(export_replay, "ROOT", source)
    output = tmp_path / "published"
    export_replay.export(output)
    (output / "archive.html").write_text("Old published page")
    (output / "encounter.0123456789abcdef.js").write_text("Stale code")
    (output / "experiments/history-v3").mkdir()
    export_replay.export(output)
    assert not (output / "archive.html").exists()
    assert not (output / "encounter.0123456789abcdef.js").exists()
    assert not (output / "experiments/history-v3").exists()
    assert (static / "archive.html").read_text() == "Historical research"
    assert (output / "experiments/encounter-v3/manifest.json").exists()
    assert (output / "assets/asset.txt").exists()


def test_export_refuses_to_replace_source_or_unmarked_directory(tmp_path):
    with pytest.raises(ValueError):
        export_replay.export(ROOT)
    with pytest.raises(ValueError):
        export_replay.export(ROOT / "static")
    with pytest.raises(ValueError):
        export_replay.export(tmp_path)

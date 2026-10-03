"""Publish-time contracts for the DOM and its matching client modules."""

import re
from pathlib import Path

from scripts.export_replay import version_interface

ROOT = Path(__file__).resolve().parents[1]


def test_client_static_ids_exist_once():
    html = (ROOT / "static/archive.html").read_text()
    ids = re.findall(r'id="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    app = (ROOT / "static/app.js").read_text()
    for name in re.findall(r"\$\('([^']+)'\)", app):
        assert name in ids, name
    assert 'id="current-verse"' not in html
    assert html.index('id="reading-heading"') < html.index('id="response-heading"')


def test_published_modules_share_content_version(tmp_path):
    (tmp_path / "index.html").write_text(
        '<script src="./app.js"></script><link href="./style.css">'
    )
    (tmp_path / "app.js").write_text("import {Audio} from './audio-player.js';")
    (tmp_path / "audio-player.js").write_text("export class Audio {}")
    (tmp_path / "style.css").write_text("body {}")
    version = version_interface(tmp_path)
    assert f"app.{version}.js" in (tmp_path / "index.html").read_text()
    assert f"audio-player.{version}.js" in (tmp_path / f"app.{version}.js").read_text()
    assert (tmp_path / f"audio-player.{version}.js").exists()


def test_comparison_dom_matches_its_client():
    html = (ROOT / "static/comparison.html").read_text()
    ids = re.findall(r'id="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    code = (ROOT / "static/comparison.js").read_text()
    for name in re.findall(r"\$\('([^']+)'\)", code):
        assert name in ids, name
    assert "<audio" not in html  # The in-app browser requires our AudioContext transport.


def test_temporal_dom_matches_its_client():
    html = (ROOT / "static/temporal.html").read_text()
    ids = re.findall(r'id="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    code = (ROOT / "static/temporal.js").read_text()
    for name in re.findall(r"\$\('([^']+)'\)", code):
        assert name in ids, name
    assert "<audio" not in html


def test_history_dom_matches_its_client():
    html = (ROOT / "static/history.html").read_text()
    ids = re.findall(r'id="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    code = (ROOT / "static/history.js").read_text()
    for name in re.findall(r"\$\('([^']+)'\)", code):
        assert name in ids, name


def test_emphasis_player_markup_contract():
    html = (ROOT / "static/archive.html").read_text()
    keys = re.findall(r'data-em="([^"]+)"', html)
    assert len(keys) == len(set(keys))
    code = (ROOT / "static/emphasis-player.js").read_text()
    for key in re.findall(r"this.q\('([^']+)'\)", code):
        assert key in keys, key


def test_passage_player_markup_contract():
    html = (ROOT / "static/archive.html").read_text()
    keys = re.findall(r'data-p="([^"]+)"', html)
    assert len(keys) == len(set(keys))
    code = (ROOT / "static/passage-player.js").read_text()
    for key in re.findall(r"this.q\('([^']+)'\)", code):
        assert key in keys, key


def test_receiver_sensitivity_mount_exists_once():
    html = (ROOT / "static/receiver.html").read_text()
    assert html.count('id="sensitivity"') == 1
    assert "./receiver-sensitivity.js" in html
    code = (ROOT / "static/receiver-sensitivity.js").read_text()
    assert "innerHTML" not in code
    assert "confidence interval" in code


def test_performance_dom_and_passage_controls_match_the_client():
    html = (ROOT / "static/performances.html").read_text()
    ids = re.findall(r'id="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    code = (ROOT / "static/performances.js").read_text()
    for name in re.findall(r"\$\('([^']+)'\)", code):
        assert name in ids, name
    assert "innerHTML" not in code
    assert "./performances.js" in html
    assert "No time warping" in (ROOT / "critic/performance_passages.py").read_text()


def test_encounter_dom_and_static_only_boundary():
    html = (ROOT / "static/index.html").read_text()
    ids = re.findall(r'id="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    code = (ROOT / "static/encounter.js").read_text()
    for name in re.findall(r"\$\([\"']([^\"']+)[\"']\)", code):
        assert name in ids, name
    assert "/api/" not in code
    assert "weights" not in code
    assert 'id="poem"' in html and "<textarea" not in html
    assert "archive.html" in html
    assert "Recorded full-connectome simulation" in code


def test_local_listening_dom_and_privacy_boundary():
    html = (ROOT / "static/index.html").read_text()
    ids = re.findall(r'id="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    code = (ROOT / "static/recording-panel.js").read_text()
    for name in re.findall(r"\$\([\"']([^\"']+)[\"']\)", code):
        assert name in ids, name
    assert "/api/" not in code
    assert "POST" not in code
    assert "sendBeacon" not in code
    assert "getUserMedia" in code
    assert 'id="process-voice"' in html
    assert "60 seconds" in html
    assert "?voice=1" in (ROOT / "static/listen.html").read_text()


def test_python_server_exposes_the_same_curated_playback_contract():
    from fastapi.testclient import TestClient

    from critic.server import app

    response = TestClient(app).get("/experiments/encounter-v2/manifest.json")
    assert response.status_code == 200
    assert response.json()["schema_version"] == "encounter-manifest-v2"


def test_legacy_api_keeps_its_amplitude_method_snapshot():
    from fastapi.testclient import TestClient

    from critic.server import app

    response = TestClient(app).get("/api/method")
    assert response.status_code == 200
    assert response.text == (ROOT / "docs/PROTOTYPE-METHOD.md").read_text()

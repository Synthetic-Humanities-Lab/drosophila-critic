from fastapi.testclient import TestClient

from critic.server import app

client = TestClient(app)


def test_invalid_submissions_and_no_cross_origin():
    assert client.post("/api/readings", json={"poem": " "}).status_code == 422
    assert client.post("/api/readings", json={"poem": "hello", "seed": 9}).status_code == 422
    assert (
        client.post(
            "/api/readings", json={"poem": "hello"}, headers={"origin": "https://elsewhere.example"}
        ).status_code
        == 403
    )
    assert client.post("/api/readings", content=b"x" * 20001).status_code == 413


def test_only_complete_allowlisted_artifacts_are_served():
    assert client.get("/api/readings/missing/result.json").status_code == 404
    assert client.get("/api/readings/validation-poem/tts.npz").status_code == 404
    assert client.get("/api/health").json()["simulation"] == "full flybrain connectome"
    assert client.get("/api/example").json()["public_domain"] is True


def test_busy_run_does_not_queue_another(monkeypatch):
    import critic.server as server

    monkeypatch.setattr(server, "active", "existing-run")
    assert client.post("/api/readings", json={"poem": "hello"}).status_code == 409


def test_blake_is_the_opening_poem():
    from critic.example import EXAMPLE_METADATA

    example = client.get("/api/example").json()
    assert example == EXAMPLE_METADATA
    assert example["author"] == "William Blake"
    assert example["title"] == "The Fly"
    assert example["poem"].startswith("Little fly,\n")
    assert example["poem"].endswith("Or if I die.")
    assert len(example["poem"].split("\n\n")) == 5


def test_public_artifacts_expire_and_storage_is_bounded(monkeypatch, tmp_path):
    import os
    import time

    import critic.server as server

    monkeypatch.setattr(server, "PUBLIC_MODE", True)
    monkeypatch.setattr(server, "RESULTS", tmp_path)
    monkeypatch.setattr(server, "active", None)
    name = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    directory = tmp_path / name
    directory.mkdir()
    (directory / "result.json").write_text("{}")
    old = time.time() - server.RETENTION_SECONDS - 10
    os.utime(directory, (old, old))
    assert client.get(f"/api/readings/{name}").status_code == 410
    assert client.get(f"/api/readings/{name}/result.json").status_code == 410
    server.prune_expired_readings()
    assert not directory.exists()
    monkeypatch.setattr(server, "MAX_SAVED_READINGS", 0)
    assert client.post("/api/readings", json={"poem": "A test."}).status_code == 503


def test_public_origin_is_checked_independently_of_proxy_scheme(monkeypatch):
    import critic.server as server

    monkeypatch.setattr(server, "PUBLIC_ORIGIN", "https://critic.example.org")
    monkeypatch.setattr(server, "active", "busy")
    assert (
        client.post(
            "/api/readings",
            json={"poem": "A test."},
            headers={"Origin": "https://critic.example.org"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/readings", json={"poem": "A test."}, headers={"Origin": "http://testserver"}
        ).status_code
        == 403
    )

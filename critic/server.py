"""Single-worker local/hosted API. Public mode uses bounded ephemeral storage."""

import json
import logging
import re
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import (
    ALLOWED_HOSTS,
    MAX_CHARACTERS,
    MAX_SAVED_READINGS,
    PUBLIC_MODE,
    PUBLIC_ORIGIN,
    RESULTS,
    RETENTION_SECONDS,
    ROOT,
)
from .example import EXAMPLE_METADATA
from .pipeline import run_reading, validate_poem

app = FastAPI(title="The Drosophila Critic", docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fly")
lock = threading.Lock()
jobs = {}
active = None
runner = None
logger = logging.getLogger("drosophila")


@app.middleware("http")
async def local_boundary(request: Request, call_next):
    if request.method == "POST":
        origin = request.headers.get("origin")
        if origin and origin != (PUBLIC_ORIGIN or str(request.base_url).rstrip("/")):
            return JSONResponse(
                {"detail": "Cross-origin submissions are disabled"}, status_code=403
            )
        try:
            length = int(request.headers.get("content-length", "0"))
        except ValueError:
            length = 100_001
        if length <= 0:
            return JSONResponse({"detail": "A Content-Length header is required"}, status_code=411)
        if length > 20_000 or len(await request.body()) > 20_000:
            return JSONResponse({"detail": "Request is too large"}, status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; media-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
    )
    return response


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    poem: str = Field(min_length=1, max_length=MAX_CHARACTERS)


def execute(identifier, poem):
    global active, runner

    def progress(stage, fraction):
        with lock:
            jobs[identifier] = {
                "id": identifier,
                "status": "running",
                "stage": stage,
                "fraction": fraction,
            }

    try:
        if runner is None:
            progress("LOADING CONNECTOME", 0)
            from .simulation import SimulationRunner

            runner = SimulationRunner()
        run_reading(poem, RESULTS / identifier, runner, progress)
        with lock:
            jobs[identifier] = {
                "id": identifier,
                "status": "complete",
                "stage": "READY FOR REPLAY",
                "fraction": 1,
            }
    except Exception as error:
        logger.exception("Reading %s failed", identifier)
        message = (
            str(error)
            if isinstance(error, ValueError)
            else "The reading failed. See the server log for details; no response was fabricated."
        )
        # The isolated TTS worker preserves user-recoverable errors in stderr.
        import subprocess

        if isinstance(error, subprocess.CalledProcessError) and "ValueError:" in (
            error.stderr or ""
        ):
            message = error.stderr.rsplit("ValueError:", 1)[-1].strip()
        with lock:
            jobs[identifier] = {
                "id": identifier,
                "status": "failed",
                "stage": "FAILED",
                "error": message,
            }
        directory = RESULTS / identifier
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "failure.json").write_text(json.dumps(jobs[identifier]))
    finally:
        with lock:
            active = None


@app.get("/api/health")
def health():
    return {"status": "ok", "simulation": "full flybrain connectome", "busy": active is not None}


@app.get("/api/example")
def example():
    return EXAMPLE_METADATA


def prune_expired_readings():
    if not PUBLIC_MODE:
        return
    cutoff = time.time() - RETENTION_SECONDS
    RESULTS.mkdir(parents=True, exist_ok=True)
    for directory in RESULTS.iterdir():
        if (
            directory.is_dir()
            and re.fullmatch(r"[a-f0-9-]{36}", directory.name)
            and directory.stat().st_mtime < cutoff
        ):
            shutil.rmtree(directory)
            jobs.pop(directory.name, None)


@app.get("/api/settings")
def settings():
    return {"public": PUBLIC_MODE, "retention_seconds": RETENTION_SECONDS if PUBLIC_MODE else None}


@app.post("/api/readings", status_code=202)
def submit(body: Submission):
    global active
    try:
        validate_poem(body.poem)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    with lock:
        if active is not None:
            raise HTTPException(409, "A fly is already running. Wait for that reading to finish.")
        prune_expired_readings()
        if PUBLIC_MODE and sum(p.is_dir() for p in RESULTS.iterdir()) >= MAX_SAVED_READINGS:
            raise HTTPException(
                503, "The public prototype's daily storage capacity is full. Try again later."
            )
        identifier = str(uuid.uuid4())
        active = identifier
        jobs[identifier] = {"id": identifier, "status": "running", "stage": "QUEUED", "fraction": 0}
        if len(jobs) > 50:
            jobs.pop(next(iter(jobs)))
    executor.submit(execute, identifier, body.poem)
    return {"id": identifier}


def result_directory(identifier):
    if not re.fullmatch(r"[a-z0-9-]{1,64}", identifier):
        raise HTTPException(404, "Unknown reading")
    return RESULTS / identifier


@app.get("/api/readings/{identifier}")
def status(identifier: str):
    directory = result_directory(identifier)
    if (
        PUBLIC_MODE
        and directory.exists()
        and directory.stat().st_mtime < time.time() - RETENTION_SECONDS
    ):
        raise HTTPException(410, "This temporary reading has expired")
    with lock:
        if identifier in jobs:
            return jobs[identifier].copy()
    if (directory / "result.json").exists():
        return {"id": identifier, "status": "complete", "stage": "READY FOR REPLAY", "fraction": 1}
    if (directory / "failure.json").exists():
        return json.loads((directory / "failure.json").read_text())
    raise HTTPException(404, "Unknown or interrupted reading")


@app.get("/api/readings/{identifier}/{artifact}")
def artifact(identifier: str, artifact: str):
    allowed = {
        "result.json",
        "audio.wav",
        "encoding.json",
        "reading-input.json",
        "spikes.npz",
        "recording-source.json",
        "original.mp3",
        "silence-spikes.npz",
        "silence-populations.npz",
        "benchmark.json",
        "neural-display.json",
        "populations.npz",
        "population_metrics.json",
        "METHOD.md",
    }
    directory = result_directory(identifier)
    if (
        PUBLIC_MODE
        and directory.exists()
        and directory.stat().st_mtime < time.time() - RETENTION_SECONDS
    ):
        raise HTTPException(410, "This temporary reading has expired")
    if (
        artifact not in allowed
        or not (directory / "result.json").exists()
        or not (directory / artifact).exists()
    ):
        raise HTTPException(404, "Artifact not available")
    return FileResponse(directory / artifact)


@app.get("/api/method")
def method():
    return FileResponse(ROOT / "METHOD.md", media_type="text/plain")


@app.get("/CRITICAL-DIRECTIONS.md")
def critical_directions():
    return FileResponse(ROOT / "docs/CRITICAL-DIRECTIONS.md", media_type="text/plain")


app.mount(
    "/experiments/delivery-v1",
    StaticFiles(directory=ROOT / "experiments/delivery-v1"),
    name="delivery-bench",
)

app.mount(
    "/experiments/temporal-v2",
    StaticFiles(directory=ROOT / "experiments/temporal-v2"),
    name="temporal-confirmation",
)

app.mount(
    "/experiments/history-v3",
    StaticFiles(directory=ROOT / "experiments/history-v3"),
    name="history-experiment",
)

app.mount(
    "/experiments/emphasis-v4",
    StaticFiles(directory=ROOT / "experiments/emphasis-v4"),
    name="emphasis-experiment",
)

app.mount(
    "/experiments/passages-v5",
    StaticFiles(directory=ROOT / "experiments/passages-v5"),
    name="passage-comparison",
)

app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="interface")

"""Single-worker local/hosted API. Public mode uses bounded ephemeral storage."""

import json
import logging
import os
import re
import secrets
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.datastructures import UploadFile
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
from .performance import MAX_FILE_BYTES, decode_upload, run_comparison
from .performance_passages import MatchedPassage, validate_windows
from .pipeline import run_reading, validate_poem

app = FastAPI(title="The Drosophila Critic", docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fly")
lock = threading.Lock()
jobs = {}
active = None
runner = None
logger = logging.getLogger("drosophila")
UPLOAD_TOKEN = os.environ.get("CRITIC_UPLOAD_TOKEN", "")


@app.middleware("http")
async def local_boundary(request: Request, call_next):
    if request.method == "POST":
        origin = request.headers.get("origin")
        if origin and origin != (PUBLIC_ORIGIN or str(request.base_url).rstrip("/")):
            return JSONResponse(
                {"detail": "Cross-origin submissions are disabled"}, status_code=403
            )
        comparison = request.url.path == "/api/comparisons"
        if comparison and PUBLIC_MODE:
            if not UPLOAD_TOKEN:
                return JSONResponse(
                    {"detail": "Recording uploads are not enabled on this host"}, status_code=503
                )
            provided = request.headers.get("authorization", "")
            if not secrets.compare_digest(provided.encode(), ("Bearer " + UPLOAD_TOKEN).encode()):
                return JSONResponse(
                    {"detail": "A valid lab upload token is required"}, status_code=401
                )
        if comparison and active is not None:
            return JSONResponse(
                {"detail": "A fly is already running. Wait for it to finish."}, status_code=409
            )
        limit = 2 * MAX_FILE_BYTES + 20_000 if comparison else 20_000
        try:
            length = int(request.headers.get("content-length", "0"))
        except ValueError:
            length = limit + 1
        if length <= 0:
            return JSONResponse({"detail": "A Content-Length header is required"}, status_code=411)
        if length > limit:
            return JSONResponse({"detail": "Request is too large"}, status_code=413)
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                return JSONResponse({"detail": "Request is too large"}, status_code=413)
            chunks.append(chunk)
        # Starlette's middleware cached request replays this bounded body downstream.
        request._body = b"".join(chunks)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; media-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
    )
    return response


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    poem: str = Field(min_length=1, max_length=MAX_CHARACTERS)


def execute(identifier, poem=None, comparison=None):
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
        if comparison is None:
            run_reading(poem, RESULTS / identifier, runner, progress)
        else:
            contents, display = comparison
            run_comparison(contents, display, RESULTS / identifier, runner, progress)
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
    return {
        "public": PUBLIC_MODE,
        "retention_seconds": RETENTION_SECONDS if PUBLIC_MODE else None,
        "comparisons_enabled": not PUBLIC_MODE or bool(UPLOAD_TOKEN),
        "upload_token_required": PUBLIC_MODE,
        "max_recording_seconds": 120,
    }


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


class ComparisonSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    poem: str = Field(min_length=1, max_length=MAX_CHARACTERS)
    label_a: str = Field(min_length=1, max_length=80)
    label_b: str = Field(min_length=1, max_length=80)
    same_poem_attested: bool
    passages: list[MatchedPassage] = Field(default_factory=list, max_length=20)
    source_sha256_a: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    source_sha256_b: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    source_format_a: str = Field(default="audio/wav", max_length=100)
    source_format_b: str = Field(default="audio/wav", max_length=100)


@app.post("/api/comparisons", status_code=202)
async def submit_comparison(request: Request):
    global active
    with lock:
        if active is not None:
            raise HTTPException(409, "A fly is already running. Wait for it to finish.")
    async with request.form(max_files=2, max_fields=1, max_part_size=16384) as form:
        if sorted(form.keys()) != ["a", "b", "metadata"] or len(form.multi_items()) != 3:
            raise HTTPException(422, "Supply recordings a and b and one metadata JSON field")
        try:
            display = ComparisonSubmission.model_validate_json(form["metadata"])
            validate_poem(display.poem)
            if not display.same_poem_attested:
                raise ValueError("Confirm that both recordings contain the same poem")
            contents, durations = {}, {}
            for name in ("a", "b"):
                upload = form[name]
                if not isinstance(upload, UploadFile):
                    raise ValueError("Recordings must be WAV file uploads")
                contents[name] = await upload.read(MAX_FILE_BYTES + 1)
                samples, info = decode_upload(contents[name])
                durations[name] = info["duration"]
                if len(samples) < 48_000:
                    raise ValueError("Each performance must be at least one second")
            validate_windows([p.model_dump() for p in display.passages], durations)
        except (ValueError, TypeError, ValidationError) as error:
            raise HTTPException(422, str(error)) from error
    with lock:
        if active is not None:
            raise HTTPException(409, "A fly is already running. Wait for it to finish.")
        prune_expired_readings()
        if PUBLIC_MODE:
            occupied = sum(p.stat().st_size for p in RESULTS.rglob("*") if p.is_file())
            reserve = 4_000_000_000
            if occupied + reserve > 10_000_000_000 or shutil.disk_usage(RESULTS).free < reserve:
                raise HTTPException(503, "Insufficient temporary space for a full comparison")
        if PUBLIC_MODE and sum(p.is_dir() for p in RESULTS.iterdir()) >= MAX_SAVED_READINGS:
            raise HTTPException(503, "Temporary storage is full; try again later")
        identifier = str(uuid.uuid4())
        active = identifier
        jobs[identifier] = {"id": identifier, "status": "running", "stage": "QUEUED", "fraction": 0}
        if len(jobs) > 50:
            jobs.pop(next(iter(jobs)))
    executor.submit(execute, identifier, comparison=(contents, display.model_dump()))
    return {"id": identifier}


@app.get("/api/comparisons/{identifier}")
def comparison_status(identifier: str):
    return status(identifier)


@app.get("/api/comparisons/{identifier}/{artifact:path}")
def comparison_artifact(identifier: str, artifact: str):
    directory = result_directory(identifier)
    status(identifier)  # Apply expiry and interrupted-job checks before serving anything.
    allowed = {
        "result.json",
        "encoding.json",
        "reading-input.json",
        "a.wav",
        "b.wav",
        "original-a.wav",
        "original-b.wav",
    }
    run_artifact = re.fullmatch(
        r"[ab]-(sound|silence)-110[1-4]/(spikes\.npz|populations\.npz|provenance\.json)", artifact
    )
    if (artifact not in allowed and not run_artifact) or not (directory / "result.json").exists():
        raise HTTPException(404, "Artifact not available")
    if not (directory / artifact).is_file():
        raise HTTPException(404, "Artifact not available")
    return FileResponse(directory / artifact)


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


@app.get("/RECEIVER-V2.md")
def receiver_method():
    return FileResponse(ROOT / "docs/RECEIVER-V2.md", media_type="text/plain")


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

app.mount(
    "/experiments/populations-v6",
    StaticFiles(directory=ROOT / "experiments/populations-v6"),
    name="population-comparison",
)

app.mount(
    "/experiments/receiver-v2",
    StaticFiles(directory=ROOT / "experiments/receiver-v2"),
    name="receiver-lab",
)

app.mount(
    "/experiments/performance-v1",
    StaticFiles(directory=ROOT / "experiments/performance-v1", check_dir=False),
    name="performance-comparison",
)

app.mount(
    "/experiments/encounter-v1",
    StaticFiles(directory=ROOT / "experiments/encounter-v1", check_dir=False),
    name="encounter-evidence",
)
app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="interface")

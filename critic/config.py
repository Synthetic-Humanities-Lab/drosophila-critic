import os
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PUBLIC_ORIGIN = os.environ.get("CRITIC_PUBLIC_ORIGIN", "").rstrip("/")
PUBLIC_MODE = bool(PUBLIC_ORIGIN)
if PUBLIC_MODE and (
    urlparse(PUBLIC_ORIGIN).scheme != "https" or not urlparse(PUBLIC_ORIGIN).hostname
):
    raise ValueError("CRITIC_PUBLIC_ORIGIN must be the exact HTTPS origin of the hosted app")
RESULTS = Path(
    os.environ.get(
        "CRITIC_RESULTS", "/tmp/drosophila-critic-results" if PUBLIC_MODE else str(ROOT / "results")
    )
)
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "testserver"]
if PUBLIC_MODE:
    ALLOWED_HOSTS.append(urlparse(PUBLIC_ORIGIN).hostname)
RETENTION_SECONDS = 86400
MAX_SAVED_READINGS = 20
UPSTREAM = ROOT / "vendor" / "fly.ai"
UPSTREAM_COMMIT = "5e931b8dc4856550565c5fa129d3d0c055af3dd1"
DT = 0.020
SEED = 64
WARMUP_SECONDS = 0.5
BASELINE_SECONDS = 1.0
TAIL_SECONDS = 1.0
MAX_AUDIO_SECONDS = 60
MAX_CHARACTERS = 2000
THREADS = 4

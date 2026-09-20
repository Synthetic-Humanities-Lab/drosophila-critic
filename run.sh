#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec .venv/bin/python -m uvicorn critic.server:app --host 127.0.0.1 --port 8765

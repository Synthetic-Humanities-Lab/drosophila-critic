"""Download and verify the two fixed local voice assets (about 354 MB)."""

import hashlib
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from critic.config import DATA
from critic.neural_tts import MODEL_FILES

base = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
directory = DATA / "tts"
directory.mkdir(parents=True, exist_ok=True)
for name, digest in MODEL_FILES.items():
    path = directory / name
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
        print(f"Verified {name}")
        continue
    temporary = path.with_suffix(path.suffix + ".part")
    print(f"Downloading {name}", flush=True)
    urllib.request.urlretrieve(base + name, temporary)
    if hashlib.sha256(temporary.read_bytes()).hexdigest() != digest:
        temporary.unlink()
        raise RuntimeError(f"Checksum mismatch: {name}")
    temporary.replace(path)

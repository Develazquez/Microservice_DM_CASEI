from __future__ import annotations

import os
from pathlib import Path
import subprocess
import time
from urllib.error import URLError
from urllib.request import urlopen


os.environ.setdefault("OLLAMA_HOST", "127.0.0.1:11434")
os.environ.setdefault("OLLAMA_MODELS", "/workspace/ollama/models")
model = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct-2507-q4_K_M")
Path(os.environ["OLLAMA_MODELS"]).mkdir(parents=True, exist_ok=True)

ollama = subprocess.Popen(["ollama", "serve"])
for _ in range(60):
    try:
        with urlopen("http://127.0.0.1:11434/api/tags", timeout=2):
            break
    except URLError:
        time.sleep(1)
else:
    ollama.terminate()
    raise RuntimeError("Ollama no inicio dentro del tiempo esperado.")

listed = subprocess.run(["ollama", "list"], check=True, capture_output=True, text=True).stdout
if model not in listed:
    subprocess.run(["ollama", "pull", model], check=True)

os.execvp(
    "uvicorn",
    ["uvicorn", "runpod_gateway.main:app", "--host", "0.0.0.0", "--port", "8001"],
)

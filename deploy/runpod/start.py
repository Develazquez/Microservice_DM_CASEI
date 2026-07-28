from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen


PROJECT_ROOT = Path("/opt/casei")
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
STOP_REQUESTED = threading.Event()


def env_flag(name: str, default: bool = False) -> bool:
    fallback = "true" if default else "false"
    return os.getenv(name, fallback).strip().lower() in {"1", "true", "yes", "on"}


def validate_worker_configuration() -> None:
    if not env_flag("CASEI_ML_WORKER_ENABLED"):
        return

    supabase_url = os.getenv("CASEI_SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    service_key = os.getenv("CASEI_SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    missing = []
    if not supabase_url:
        missing.append("CASEI_SUPABASE_URL")
    if not service_key:
        missing.append("CASEI_SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        raise RuntimeError(
            "El worker ML esta habilitado pero faltan secretos de servidor: "
            + ", ".join(missing)
        )


def wait_for_ollama(process: subprocess.Popen[bytes]) -> None:
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError(
                f"Ollama termino durante el arranque con codigo {process.returncode}."
            )
        try:
            with urlopen(OLLAMA_TAGS_URL, timeout=2):
                return
        except (URLError, TimeoutError, OSError):
            time.sleep(1)
    raise RuntimeError("Ollama no inicio dentro del tiempo esperado.")


def ensure_models() -> None:
    model = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct-2507-q4_K_M")
    embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:0.6b")
    listed = subprocess.run(
        ["ollama", "list"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    for required_model in [model, embedding_model]:
        if required_model not in listed:
            print(f"Descargando modelo requerido: {required_model}", flush=True)
            subprocess.run(["ollama", "pull", required_model], check=True)


def start_process(name: str, command: list[str]) -> subprocess.Popen[bytes]:
    print(f"Iniciando {name}: {' '.join(command)}", flush=True)
    return subprocess.Popen(command, cwd=PROJECT_ROOT)


def stop_processes(processes: dict[str, subprocess.Popen[bytes]]) -> None:
    for process in processes.values():
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 15
    for process in processes.values():
        if process.poll() is not None:
            continue
        try:
            process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            process.kill()


def request_stop(_signum: int, _frame: object) -> None:
    STOP_REQUESTED.set()


def main() -> None:
    os.environ.setdefault("OLLAMA_HOST", "127.0.0.1:11434")
    os.environ.setdefault("OLLAMA_MODELS", "/workspace/ollama/models")
    Path(os.environ["OLLAMA_MODELS"]).mkdir(parents=True, exist_ok=True)
    validate_worker_configuration()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    processes: dict[str, subprocess.Popen[bytes]] = {}
    try:
        processes["ollama"] = start_process("Ollama", ["ollama", "serve"])
        wait_for_ollama(processes["ollama"])
        ensure_models()
        processes["gateway"] = start_process(
            "gateway CASEI",
            [
                sys.executable,
                "-m",
                "uvicorn",
                "runpod_gateway.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8001",
            ],
        )
        if env_flag("CASEI_ML_WORKER_ENABLED"):
            processes["worker"] = start_process(
                "worker ML",
                [sys.executable, "-u", "scripts/run_ml_worker.py"],
            )
        else:
            print(
                "Worker ML desactivado. Define CASEI_ML_WORKER_ENABLED=true para habilitarlo.",
                flush=True,
            )

        while not STOP_REQUESTED.wait(1):
            for name, process in processes.items():
                return_code = process.poll()
                if return_code is not None:
                    raise RuntimeError(
                        f"El proceso {name} termino inesperadamente con codigo {return_code}."
                    )
    finally:
        stop_processes(processes)


if __name__ == "__main__":
    main()

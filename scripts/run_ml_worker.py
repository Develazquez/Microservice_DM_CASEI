from __future__ import annotations

from pathlib import Path
import json
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.models.config import CASEI_ML_POLL_SECONDS, CASEI_ML_WORKER_ENABLED
from app.services.ml_worker_service import worker_once


def main() -> None:
    if not CASEI_ML_WORKER_ENABLED:
        print("Worker desactivado por CASEI_ML_WORKER_ENABLED=false")
        return
    print("CASEI ML worker iniciado. Presiona Ctrl+C para detenerlo.")
    while True:
        try:
            result = worker_once()
            if result.get("status") != "idle":
                print(json.dumps(result, ensure_ascii=False, default=str))
        except KeyboardInterrupt:
            print("Worker detenido.")
            return
        except Exception as exc:
            print(f"Error de worker: {exc}")
        time.sleep(max(1.0, CASEI_ML_POLL_SECONDS))


if __name__ == "__main__":
    main()

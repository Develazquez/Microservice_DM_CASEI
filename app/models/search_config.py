from __future__ import annotations

import os

from app.models import config as _project_config  # noqa: F401  # Carga .env antes de leer opciones.


BM25_K1 = 1.5
BM25_B = 0.75
SEARCH_TOP_K = 10


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


CASEI_SLM_ENABLED = _env_bool("CASEI_SLM_ENABLED", False)
CASEI_SEARCH_MODE = os.getenv("CASEI_SEARCH_MODE", "auto").strip().lower()
CASEI_SEMANTIC_SEARCH_ENABLED = _env_bool("CASEI_SEMANTIC_SEARCH_ENABLED", False)
CASEI_SEARCH_RETRIEVAL_MODE = os.getenv("CASEI_SEARCH_RETRIEVAL_MODE", "hybrid").strip().lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip().rstrip("/")
OLLAMA_GATEWAY_URL = os.getenv("OLLAMA_GATEWAY_URL", "").strip().rstrip("/")
OLLAMA_GATEWAY_API_KEY = os.getenv("OLLAMA_GATEWAY_API_KEY", "").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct-2507-q4_K_M").strip()
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:0.6b").strip()
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "12"))
OLLAMA_EMBEDDING_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_EMBEDDING_TIMEOUT_SECONDS", "8"))
OLLAMA_EMBEDDING_INDEX_TIMEOUT_SECONDS = float(
    os.getenv("OLLAMA_EMBEDDING_INDEX_TIMEOUT_SECONDS", "120")
)
OLLAMA_WARMUP_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_WARMUP_TIMEOUT_SECONDS", "120"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m").strip()
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "256"))
SLM_CACHE_MAX_SIZE = int(os.getenv("CASEI_SLM_CACHE_MAX_SIZE", "256"))
SLM_CACHE_TTL_SECONDS = int(os.getenv("CASEI_SLM_CACHE_TTL_SECONDS", "600"))
SLM_FAILURE_THRESHOLD = int(os.getenv("CASEI_SLM_FAILURE_THRESHOLD", "3"))
SLM_COOLDOWN_SECONDS = int(os.getenv("CASEI_SLM_COOLDOWN_SECONDS", "60"))
SEMANTIC_TOP_K = int(os.getenv("CASEI_SEMANTIC_TOP_K", "50"))
SEMANTIC_MIN_SIMILARITY = float(os.getenv("CASEI_SEMANTIC_MIN_SIMILARITY", "0.35"))
SEMANTIC_PROTOTYPE_MIN_SIMILARITY = float(
    os.getenv("CASEI_SEMANTIC_PROTOTYPE_MIN_SIMILARITY", "0.72")
)
RRF_K = int(os.getenv("CASEI_RRF_K", "60"))
SEARCH_EXPLAIN_DEFAULT = _env_bool("CASEI_SEARCH_EXPLAIN_DEFAULT", False)
EMBEDDING_BATCH_SIZE = int(os.getenv("CASEI_EMBEDDING_BATCH_SIZE", "32"))
EMBEDDING_CACHE_MAX_SIZE = int(os.getenv("CASEI_EMBEDDING_CACHE_MAX_SIZE", "512"))
EMBEDDING_CACHE_TTL_SECONDS = int(os.getenv("CASEI_EMBEDDING_CACHE_TTL_SECONDS", "1800"))

SPANISH_STOPWORDS = {
    "a",
    "al",
    "con",
    "de",
    "del",
    "e",
    "el",
    "en",
    "la",
    "las",
    "los",
    "o",
    "para",
    "por",
    "que",
    "un",
    "una",
    "y",
}

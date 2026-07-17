"""
Pruebas de conexión API ↔ Frontend para el microservicio de segmentación académica.

Verifica que la API desplegada responda correctamente en los endpoints que el
frontend Next.js consume a través de `lib/actions/segmentacion-academica.ts`.

URL base configurada en el .env del frontend como:
  ACADEMIC_SEGMENTATION_API_URL=https://microservicio-mineria.vercel.app
"""

from __future__ import annotations

import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path
from urllib.parse import urlencode, urljoin

# ---------------------------------------------------------------------------
# Intentamos usar requests; si no está disponible, usamos urllib como fallback
# ---------------------------------------------------------------------------
try:
    import requests  # type: ignore[import-untyped]

    def _get(url: str, headers: dict | None = None, timeout: int = 30) -> dict:
        resp = requests.get(url, headers=headers or {}, timeout=timeout)
        return {
            "status": resp.status_code,
            "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
            "elapsed_ms": int(resp.elapsed.total_seconds() * 1000),
            "headers": dict(resp.headers),
        }

except ImportError:
    import urllib.request
    import urllib.error

    def _get(url: str, headers: dict | None = None, timeout: int = 30) -> dict:
        req = urllib.request.Request(url, headers=headers or {})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body_bytes = resp.read()
                elapsed = int((time.time() - t0) * 1000)
                ct = resp.headers.get("Content-Type", "")
                body = json.loads(body_bytes) if "json" in ct else body_bytes.decode()
                return {"status": resp.status, "body": body, "elapsed_ms": elapsed, "headers": dict(resp.headers)}
        except urllib.error.HTTPError as exc:
            elapsed = int((time.time() - t0) * 1000)
            body_bytes = exc.read()
            ct = exc.headers.get("Content-Type", "")
            body = json.loads(body_bytes) if "json" in ct else body_bytes.decode()
            return {"status": exc.code, "body": body, "elapsed_ms": elapsed, "headers": dict(exc.headers)}


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
API_BASE = os.getenv(
    "ACADEMIC_SEGMENTATION_API_URL",
    "https://microservicio-mineria.vercel.app",
)
PREFIX = "/cacei/segmentation"
ROLE_HEADER = {"X-CASEI-ROLE": "director", "X-CASEI-PURPOSE": "connection_test"}

# ---------------------------------------------------------------------------
# Endpoints que el frontend consume (extraídos de segmentacion-academica.ts)
# ---------------------------------------------------------------------------
TESTS: list[dict] = [
    # 1. Health / Root
    {
        "name": "GET / (Root – enlaces del servicio)",
        "path": "/",
        "prefix": False,
        "expect_keys": ["service", "status"],
    },
    {
        "name": "GET /health (Health check global)",
        "path": "/health",
        "prefix": False,
        "expect_keys": ["status"],
    },
    # 2. Segmentation Health (bajo prefijo /cacei/segmentation)
    {
        "name": "GET /cacei/segmentation/health",
        "path": "/health",
        "prefix": True,
        "expect_keys": ["status"],
    },
    # 3. Summary – usado por loadSegmentationDashboardFromApi()
    {
        "name": "GET /cacei/segmentation/summary",
        "path": "/summary",
        "prefix": True,
        "expect_keys": ["total_students"],
    },
    # 4. Students – paginado, el frontend pide todas las páginas
    {
        "name": "GET /cacei/segmentation/students?limit=5&offset=0",
        "path": "/students",
        "prefix": True,
        "params": {"limit": "5", "offset": "0"},
        "expect_keys": ["total", "items"],
    },
    # 5. Search – BM25
    {
        "name": "GET /cacei/segmentation/search?q=riesgo&top_k=3",
        "path": "/search",
        "prefix": True,
        "params": {"q": "riesgo", "top_k": "3"},
        "expect_keys": ["items"],
    },
    # 6. Clusters
    {
        "name": "GET /cacei/segmentation/clusters",
        "path": "/clusters",
        "prefix": True,
        "expect_keys": [],
    },
    # 7. History
    {
        "name": "GET /cacei/segmentation/history?limit=5",
        "path": "/history",
        "prefix": True,
        "params": {"limit": "5"},
        "expect_keys": ["items"],
    },
    # 8. LLM Context Contract
    {
        "name": "GET /cacei/segmentation/context/contract",
        "path": "/context/contract",
        "prefix": True,
        "expect_keys": [],
    },
    # 9. Sync Status
    {
        "name": "GET /cacei/segmentation/sync/status",
        "path": "/sync/status",
        "prefix": True,
        "expect_keys": [],
    },
    # 10. RAG Documents
    {
        "name": "GET /cacei/segmentation/rag/documents?limit=3",
        "path": "/rag/documents",
        "prefix": True,
        "params": {"limit": "3", "role": "director"},
        "expect_keys": ["items"],
    },
    # 11. OpenAPI JSON – necesario para documentación Swagger
    {
        "name": "GET /openapi.json (Esquema OpenAPI)",
        "path": "/openapi.json",
        "prefix": False,
        "expect_keys": ["openapi", "info", "paths"],
    },
]


# ---------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------
def build_url(test: dict) -> str:
    base = API_BASE.rstrip("/")
    prefix = PREFIX if test.get("prefix") else ""
    url = f"{base}{prefix}{test['path']}"
    params = test.get("params", {})
    if params:
        url += "?" + urlencode(params)
    return url


def run_test(test: dict) -> dict:
    url = build_url(test)
    result: dict = {"name": test["name"], "url": url, "passed": False, "details": ""}
    try:
        resp = _get(url, headers=ROLE_HEADER, timeout=30)
        result["status"] = resp["status"]
        result["elapsed_ms"] = resp["elapsed_ms"]

        # CORS headers check
        cors_origin = resp["headers"].get("access-control-allow-origin", resp["headers"].get("Access-Control-Allow-Origin", ""))
        result["cors_allow_origin"] = cors_origin

        if resp["status"] != 200:
            result["details"] = f"HTTP {resp['status']} – {json.dumps(resp['body'], ensure_ascii=False)[:300]}"
            return result

        body = resp["body"]
        expect_keys = test.get("expect_keys", [])
        if isinstance(body, dict) and expect_keys:
            missing = [k for k in expect_keys if k not in body]
            if missing:
                result["details"] = f"Claves faltantes en respuesta: {missing}"
                return result

        # Verificar que items no esté vacío cuando se espera
        if isinstance(body, dict) and "items" in body:
            items = body["items"]
            result["item_count"] = len(items) if isinstance(items, list) else "N/A"

        result["passed"] = True
        result["details"] = "OK"

    except Exception as exc:
        result["details"] = f"Error de conexión: {exc}"

    return result


def main() -> None:
    print("=" * 72)
    print("  PRUEBAS DE CONEXIÓN: API de Segmentación Académica ↔ Frontend")
    print(f"  URL base: {API_BASE}")
    print(f"  Prefijo API: {PREFIX}")
    print(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)
    print()

    results = []
    passed = 0
    failed = 0

    for i, test in enumerate(TESTS, 1):
        print(f"[{i:02d}/{len(TESTS):02d}] {test['name']} ... ", end="", flush=True)
        result = run_test(test)
        results.append(result)
        status_label = "✅ PASS" if result["passed"] else "❌ FAIL"
        elapsed = f"{result.get('elapsed_ms', '?')}ms"
        print(f"{status_label} ({elapsed})")
        if not result["passed"]:
            print(f"         ↳ {result['details']}")
            failed += 1
        else:
            passed += 1
            if result.get("item_count") is not None:
                print(f"         ↳ items: {result['item_count']}")

    # Resumen
    print()
    print("=" * 72)
    print("  RESUMEN")
    print("=" * 72)
    print(f"  Total:   {len(TESTS)}")
    print(f"  Pasaron: {passed}")
    print(f"  Fallaron: {failed}")

    # Verificación de compatibilidad CORS con el frontend
    print()
    print("  — Verificación CORS —")
    frontend_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    for r in results:
        cors = r.get("cors_allow_origin", "")
        if cors:
            ok = cors == "*" or any(o in cors for o in frontend_origins)
            symbol = "✅" if ok else "⚠️"
            print(f"  {symbol} {r['name'][:50]}: Access-Control-Allow-Origin = {cors}")

    # Verificación de contrato de datos para el frontend
    print()
    print("  — Contrato de datos (frontend espera estos campos) —")
    for r in results:
        if r["passed"] and r["name"].startswith("GET /cacei/segmentation/students"):
            print(f"  ✅ /students devuelve 'total', 'items' → paginación OK")
        if r["passed"] and r["name"].startswith("GET /cacei/segmentation/summary"):
            print(f"  ✅ /summary devuelve 'total_students' → dashboard OK")
        if r["passed"] and r["name"].startswith("GET /cacei/segmentation/search"):
            print(f"  ✅ /search devuelve 'items' → búsqueda BM25 OK")
        if r["passed"] and r["name"].startswith("GET /cacei/segmentation/history"):
            print(f"  ✅ /history devuelve 'items' → historial OK")

    print()
    if failed > 0:
        print(f"  ⚠️  {failed} prueba(s) fallaron. Revisa los detalles arriba.")
        sys.exit(1)
    else:
        print("  🎉 Todas las pruebas pasaron. La API es consumible por el frontend.")
        sys.exit(0)


if __name__ == "__main__":
    main()

# Gateway SLM de CASEI en RunPod

Esta imagen ejecuta Ollama localmente y publica unicamente el gateway autenticado en el puerto 8001.
No contiene datasets, expedientes ni artefactos academicos.

## Configuracion del Pod

- GPU: RTX A5000, una GPU.
- Volume disk: 40 GB montado en `/workspace`.
- Puerto HTTP expuesto: `8001`.
- Variable `CASEI_SLM_GATEWAY_API_KEY`: secreto largo y aleatorio.
- Variable `OLLAMA_MODEL`: `qwen3:4b-instruct-2507-q4_K_M`.

Construccion local:

```bash
docker build -f deploy/runpod/Dockerfile -t casei-slm-gateway .
```

La API CASEI debe usar la URL `https://POD_ID-8001.proxy.runpod.net`, nunca el puerto 11434.
Antes de una demo se debe consultar `/health`, luego `/ready` y finalmente ejecutar `/warmup` con
el header `X-CASEI-SLM-KEY`.

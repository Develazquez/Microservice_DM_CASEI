# Gateway de modelos y worker ML de CASEI en RunPod

Para actualizar un Pod existente, seguir
[`GUIA_ACTUALIZACION_DESPLIEGUE.md`](GUIA_ACTUALIZACION_DESPLIEGUE.md).

Esta imagen ejecuta tres procesos supervisados:

1. Ollama para Qwen Instruct y Qwen Embedding.
2. El gateway autenticado en el puerto 8001.
3. El worker persistente que reclama `ml_model_runs` desde Supabase.

El gateway sigue siendo el unico servicio HTTP expuesto. El worker no abre un
puerto; consulta la cola en Supabase y ejecuta sincronizacion, inferencia o
reentrenamiento en segundo plano.

## Configuracion de hardware

- GPU recomendada: RTX 4000 Ada o RTX A4000, una GPU.
- Volume disk: 40 GB montado en `/workspace`.
- Puerto HTTP expuesto: `8001`.

## Secretos obligatorios

- `CASEI_SLM_GATEWAY_API_KEY`: secreto largo y aleatorio para el gateway.
- `CASEI_SUPABASE_URL`: URL del proyecto Supabase.
- `CASEI_SUPABASE_SERVICE_ROLE_KEY`: service role, solo como secreto de RunPod.

Nunca publiques `CASEI_SUPABASE_SERVICE_ROLE_KEY` en el frontend, logs, imagen
Docker o repositorio.

## Variables del gateway

- Variable `CASEI_SLM_GATEWAY_API_KEY`: secreto largo y aleatorio.
- Variable `OLLAMA_MODEL`: `qwen3:4b-instruct-2507-q4_K_M`.
- Variable `OLLAMA_EMBEDDING_MODEL`: `qwen3-embedding:0.6b`.
- Variable `OLLAMA_MAX_LOADED_MODELS`: `2` para GPU de 8 GB o mas.
- Variable `OLLAMA_NUM_PARALLEL`: `1`.

## Variables del worker

```env
CASEI_ENVIRONMENT=production
CASEI_ML_WORKER_ENABLED=true
CASEI_AUTO_INFERENCE_ENABLED=true
CASEI_ML_WORKER_ID=worker-runpod-1
CASEI_ML_POLL_SECONDS=5
CASEI_ML_JOB_TIMEOUT_SECONDS=900
CASEI_ML_EVENT_DEBOUNCE_SECONDS=60
CASEI_PIPELINE_DATA_SOURCE=auto
CASEI_MODEL_ACTIVATION_MODE=manual
CASEI_STRICT_BUNDLE_CHECKSUMS=true
CASEI_ALLOW_DEV_IDENTITY_HEADERS=false
CASEI_SQLITE_HISTORY=disabled
```

La imagen incluye el bundle activo y los archivos base requeridos por el
pipeline. Los datos institucionales actuales se sincronizan desde Supabase al
reclamar cada trabajo. El sistema de archivos del contenedor no sustituye a
Supabase como fuente institucional.

Construccion local:

```bash
docker build -f deploy/runpod/Dockerfile -t casei-slm-gateway .
```

La API CASEI debe usar la URL `https://POD_ID-8001.proxy.runpod.net`, nunca el puerto 11434.
El gateway expone `/interpret` para Qwen Instruct y `/embed` para Qwen Embedding. Ambos requieren
el header `X-CASEI-SLM-KEY`.

Antes de una demo se debe consultar `/health`, luego `/ready` y finalmente ejecutar `/warmup`. En
RunPod Serverless Flex este warmup debe realizarse con anticipacion porque un cold start puede incluir
inicio del contenedor y carga de ambos modelos.

En los logs deben aparecer estas lineas:

```text
Iniciando Ollama
Iniciando gateway CASEI
Iniciando worker ML
CASEI ML worker iniciado
```

Un trabajo correcto cambia de `queued` a `claimed`, registra
`claimed_by=worker-runpod-1` y termina en `completed`.

# Despliegue CPU de API y worker CASEI

Esta es una alternativa para separar el worker del Pod GPU. No debe levantarse
al mismo tiempo que el worker de RunPod salvo que se busque concurrencia
controlada con identificadores de worker distintos.

Esta configuracion ejecuta dos procesos separados desde la misma imagen:

- `api`: FastAPI, consultas, autenticacion y encolado de trabajos.
- `worker`: sincronizacion, inferencia, reentrenamiento y publicacion.

Qwen/Ollama no se ejecuta en esta imagen. El gateway SLM puede permanecer en
RunPod aunque el worker se aloje aqui.

## Preparacion

1. Copiar `.env.production.example` como `.env.production` dentro de este directorio.
2. Completar URLs y secretos sin prefijo `NEXT_PUBLIC_` para la service role.
3. Mantener `CASEI_AUTO_INFERENCE_ENABLED=false` durante staging.
4. Ejecutar `docker compose -f deploy/cpu/docker-compose.production.yml up --build -d` desde la raiz.

Los directorios `artifacts` y `data` se montan desde el host para que API y worker compartan
el bundle activo y sobrevivan reinicios. Para multiples maquinas debe sustituirse este volumen
por almacenamiento de objetos versionado antes de activar reentrenamiento productivo.

## Validacion

- `GET http://localhost:8000/health`
- `GET http://localhost:8000/cacei/segmentation/health`
- Revisar logs: `docker compose -f deploy/cpu/docker-compose.production.yml logs -f api worker`
- Ejecutar una corrida manual en staging y comprobar su `execution_id` en Supabase.

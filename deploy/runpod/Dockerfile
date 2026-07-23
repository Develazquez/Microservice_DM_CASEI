FROM ollama/ollama:latest

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/casei
COPY deploy/runpod/requirements.txt /opt/casei/deploy/runpod/requirements.txt
RUN python3 -m pip install --no-cache-dir --break-system-packages -r /opt/casei/deploy/runpod/requirements.txt

COPY app /opt/casei/app
COPY runpod_gateway /opt/casei/runpod_gateway
COPY scripts/run_ml_worker.py /opt/casei/scripts/run_ml_worker.py
COPY artifacts /opt/casei/artifacts
COPY data/raw /opt/casei/data/raw
COPY data/processed /opt/casei/data/processed
COPY data/reports/*.csv /opt/casei/data/reports/
COPY data/storage/segmentation_inference_schema.sql /opt/casei/data/storage/segmentation_inference_schema.sql
COPY deploy/runpod/start.py /opt/casei/deploy/runpod/start.py

ENV PYTHONPATH=/opt/casei \
    PYTHONUNBUFFERED=1 \
    OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_MODELS=/workspace/ollama/models \
    CASEI_ML_WORKER_ENABLED=false

EXPOSE 8001
ENTRYPOINT ["python3", "/opt/casei/deploy/runpod/start.py"]

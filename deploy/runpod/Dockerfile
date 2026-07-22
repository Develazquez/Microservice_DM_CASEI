FROM ollama/ollama:latest

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/casei
COPY deploy/runpod/requirements.txt /opt/casei/deploy/runpod/requirements.txt
RUN python3 -m pip install --no-cache-dir --break-system-packages -r /opt/casei/deploy/runpod/requirements.txt

COPY app /opt/casei/app
COPY runpod_gateway /opt/casei/runpod_gateway
COPY deploy/runpod/start.py /opt/casei/deploy/runpod/start.py

ENV PYTHONPATH=/opt/casei \
    OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_MODELS=/workspace/ollama/models

EXPOSE 8001
ENTRYPOINT ["python3", "/opt/casei/deploy/runpod/start.py"]

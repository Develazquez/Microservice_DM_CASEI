FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/casei

WORKDIR /opt/casei

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts/run_ml_worker.py ./scripts/run_ml_worker.py
COPY artifacts ./artifacts
COPY data/raw ./data/raw
COPY data/processed ./data/processed
COPY data/reports/*.csv ./data/reports/
COPY data/storage/segmentation_inference_schema.sql ./data/storage/segmentation_inference_schema.sql

RUN useradd --create-home --uid 10001 casei \
    && chown -R casei:casei /opt/casei
USER casei

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

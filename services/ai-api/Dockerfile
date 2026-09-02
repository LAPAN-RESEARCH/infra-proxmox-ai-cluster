FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_CACHE=/home/app/.cache/huggingface/hub \
    SENTENCE_TRANSFORMERS_HOME=/home/app/.cache/huggingface/hub

RUN useradd --create-home --uid 1000 app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p /home/app/.cache/huggingface/hub && chown -R app:app /home/app /app

USER app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import json, urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=5).read()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

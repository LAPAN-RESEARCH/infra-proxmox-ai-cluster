# Escuta clínica LAPAN — imagem CPU (API/UI/worker). Para GPU completa
# (ASR embedded + diarização + enrollment): --build-arg EXTRAS=gpu.
FROM python:3.12-slim

ARG EXTRAS=""
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-gpu.txt* ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$EXTRAS" = "gpu" ]; then pip install --no-cache-dir -r requirements-gpu.txt; fi

COPY escuta ./escuta
ENV PYTHONUNBUFFERED=1
EXPOSE 8020
CMD ["uvicorn", "escuta.api:app", "--host", "0.0.0.0", "--port", "8020"]

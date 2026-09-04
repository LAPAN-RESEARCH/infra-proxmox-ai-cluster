ARG JUPYTER_BASE_TAG=2026-05-11
ARG UV_VERSION=latest

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv
FROM quay.io/jupyter/minimal-notebook:${JUPYTER_BASE_TAG}

USER root

COPY --from=uv /uv /uvx /usr/local/bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    poppler-utils \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER ${NB_UID}

ENV UV_SYSTEM_PYTHON=1
ENV UV_NO_CACHE=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN uv pip install \
    polars \
    pyarrow \
    duckdb \
    qdrant-client \
    neo4j \
    PyYAML \
    bibtexparser \
    rapidfuzz \
    rank-bm25 \
    beautifulsoup4 \
    markdownify \
    ebooklib \
    python-docx \
    python-pptx \
    pypdf \
    pymupdf \
    docling \
    fastembed \
    sentence-transformers \
    networkx \
    numpy \
    scipy \
    scikit-learn \
    matplotlib \
    llama-index \
    llama-index-vector-stores-qdrant \
    llama-index-llms-ollama \
    llama-index-embeddings-ollama \
    langchain \
    langchain-community \
    langchain-ollama \
    watchdog \
    python-dotenv \
    rich \
    ipywidgets

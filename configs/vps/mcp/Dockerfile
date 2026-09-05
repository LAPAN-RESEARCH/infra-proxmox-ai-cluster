FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir "fastmcp>=2.11,<3" httpx
COPY server.py .
EXPOSE 8000
CMD ["python", "server.py"]

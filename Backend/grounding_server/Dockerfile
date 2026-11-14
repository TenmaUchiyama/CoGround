FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml ./
COPY coground_server ./coground_server
RUN pip install -e ".[dev]"

COPY tests ./tests
COPY scripts ./scripts

EXPOSE 8000
CMD ["python", "-m", "coground_server", "--host", "0.0.0.0", "--port", "8000"]

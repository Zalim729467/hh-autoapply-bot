# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system deps (minimal for stage 1: postgres client libs already in asyncpg wheel)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (cache layer)
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# Copy source
COPY . .

CMD ["python", "-m", "bot"]

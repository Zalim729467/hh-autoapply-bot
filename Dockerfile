# syntax=docker/dockerfile:1.7
# Use official Playwright image (Ubuntu + Python + Chromium + system deps preinstalled).
FROM mcr.microsoft.com/playwright/python:v1.48.0-noble AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1

WORKDIR /app

# Install Python deps first (cache layer)
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# Make sure chromium is available (already in base image, but re-run is a no-op safety net)
RUN python -m playwright install chromium

# Copy source
COPY . .

CMD ["python", "-m", "bot"]

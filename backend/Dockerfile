# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

# Install dependencies first, from the manifest alone, so this layer (and
# pip's download cache) survives source-code-only changes below.
COPY pyproject.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/pip pip install .

COPY backend ./backend
COPY config ./config
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-deps .

EXPOSE 8000
CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]


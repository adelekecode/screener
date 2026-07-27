# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first, from the manifest alone, so this layer (and
# pip's download cache) survives source-code-only changes below.
COPY pyproject.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/pip pip install .

COPY backend ./backend
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-deps .
COPY dashboard ./dashboard

WORKDIR /app/dashboard
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]


# syntax=docker/dockerfile:1.7
# ---------- builder ---------------------------------------------------------
FROM python:3.12-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY analysis-engine /build/analysis-engine
COPY worker /build/worker
COPY shared /build/shared

RUN python -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --upgrade pip \
    && pip install /build/analysis-engine \
    && pip install /build/worker

# ---------- runtime ---------------------------------------------------------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH" PYTHONPATH="/home/worker"

# git is required by the engine's GitCloner; libpq for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
        git libpq5 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --system worker && useradd --system --gid worker --home /home/worker worker
RUN mkdir -p /var/lib/codesensei/workspaces && chown -R worker:worker /var/lib/codesensei

COPY --from=builder /opt/venv /opt/venv
COPY shared /home/worker/shared
# The worker persists results through the backend's SQLAlchemy ORM models.
# They only depend on SQLAlchemy (already installed), so we copy just the
# `app` package onto PYTHONPATH rather than installing the full backend.
COPY backend/app /home/worker/app
USER worker
WORKDIR /home/worker

ENTRYPOINT ["python", "-m", "worker.app"]

# ----------------------------------------------------------------------------
# Multi-stage Dockerfile — slim, non-root, cached deps
# ----------------------------------------------------------------------------

# ---- builder ---------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

# Copy analysis-engine first (needed by backend)
COPY analysis-engine/pyproject.toml ./analysis-engine/
COPY analysis-engine/README.md ./analysis-engine/
COPY analysis-engine/engine ./analysis-engine/engine

COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY shared ./shared

# Install backend first (pins fastapi==0.115.0), then analysis-engine
# This ensures chromadb uses the pinned fastapi version
RUN pip install --upgrade pip wheel \
 && pip install --prefix=/install . \
 && pip install --prefix=/install ./analysis-engine

# ---- runtime ---------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:${PATH}" \
    PYTHONPATH="/app:/install/lib/python3.12/site-packages"

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd  --system --gid app --home-dir /app --shell /sbin/nologin app

WORKDIR /app

COPY --from=builder /install /install
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
COPY shared ./shared

RUN mkdir -p /var/lib/codesensei/workspaces \
 && chown -R app:app /app /var/lib/codesensei

USER app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]

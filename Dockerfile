# syntax=docker/dockerfile:1.7

ARG PYTHON_BASE_IMAGE=ghcr.io/astral-sh/uv:python3.12-bookworm-slim
ARG PLAYWRIGHT_PYTHON_BASE_IMAGE=mcr.microsoft.com/playwright/python:v1.58.0-noble
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.7.22

FROM ${UV_IMAGE} AS uv-bin

FROM ${PYTHON_BASE_IMAGE} AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_PYTHON_PREFERENCE=only-system \
    UV_PYTHON_DOWNLOADS=never \
    UV_CACHE_DIR=/root/.cache/uv \
    UV_HTTP_RETRIES=8 \
    UV_HTTP_TIMEOUT=120 \
    UV_NATIVE_TLS=true \
    UV_CONCURRENT_DOWNLOADS=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv-bin /uv /uvx /usr/local/bin/

COPY . .

ARG CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml
ENV CORTEX_RUNTIME_CONFIG_PATH=${CORTEX_RUNTIME_CONFIG_PATH}

FROM ${PLAYWRIGHT_PYTHON_BASE_IMAGE} AS browser-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_PYTHON_PREFERENCE=only-system \
    UV_PYTHON_DOWNLOADS=never \
    UV_CACHE_DIR=/root/.cache/uv \
    UV_HTTP_RETRIES=8 \
    UV_HTTP_TIMEOUT=120 \
    UV_NATIVE_TLS=true \
    UV_CONCURRENT_DOWNLOADS=1 \
    CORTEX_PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv-bin /uv /uvx /usr/local/bin/

COPY . .

ARG CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml
ENV CORTEX_RUNTIME_CONFIG_PATH=${CORTEX_RUNTIME_CONFIG_PATH}

FROM browser-base AS api

ARG CORTEX_PREPARE_CRAWL4AI_RUNTIME=1

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-api --no-default-groups --frozen

RUN if [ "${CORTEX_PREPARE_CRAWL4AI_RUNTIME}" = "1" ]; then \
      ./.venv/bin/python scripts/runtime/prepare_crawl4ai_runtime.py \
      --runtime-config "${CORTEX_RUNTIME_CONFIG_PATH}" \
      --no-probe; \
    else \
      echo "[cortex] skipping Crawl4AI runtime preparation during api image build"; \
    fi

EXPOSE 8080

ENTRYPOINT ["bash", "scripts/runtime/start-api.sh"]

FROM browser-base AS parse-worker

ARG CORTEX_PREPARE_CRAWL4AI_RUNTIME=1

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-worker-parse --no-default-groups --frozen

RUN if [ "${CORTEX_PREPARE_CRAWL4AI_RUNTIME}" = "1" ]; then \
      ./.venv/bin/python scripts/runtime/prepare_crawl4ai_runtime.py \
      --runtime-config "${CORTEX_RUNTIME_CONFIG_PATH}" \
      --no-probe; \
    else \
      echo "[cortex] skipping Crawl4AI runtime preparation during parse-worker image build"; \
    fi

ENTRYPOINT ["bash", "scripts/runtime/start-parse-worker.sh"]

FROM browser-base AS parse-worker-docling

ARG CORTEX_PREPARE_CRAWL4AI_RUNTIME=1

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-worker-parse --extra docling --no-default-groups --frozen

RUN if [ "${CORTEX_PREPARE_CRAWL4AI_RUNTIME}" = "1" ]; then \
      ./.venv/bin/python scripts/runtime/prepare_crawl4ai_runtime.py \
      --runtime-config "${CORTEX_RUNTIME_CONFIG_PATH}" \
      --no-probe; \
    else \
      echo "[cortex] skipping Crawl4AI runtime preparation during docling parse-worker image build"; \
    fi

ENTRYPOINT ["bash", "scripts/runtime/start-parse-worker.sh"]

FROM python-base AS knowledge-worker

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-worker-knowledge --no-default-groups --frozen

ENTRYPOINT ["bash", "scripts/runtime/start-knowledge-worker.sh"]

FROM python-base AS evaluation-worker

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-worker-evaluation --no-default-groups --frozen

ENTRYPOINT ["bash", "scripts/runtime/start-evaluation-worker.sh"]

FROM python-base AS evaluation-worker-runtime

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-worker-evaluation --extra runtime --no-default-groups --frozen

ENTRYPOINT ["bash", "scripts/runtime/start-evaluation-worker.sh"]

FROM python-base AS synthesis-worker

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-worker-synthesis --no-default-groups --frozen

ENTRYPOINT ["bash", "scripts/runtime/start-synthesis-worker.sh"]

FROM python-base AS synthesis-worker-runtime

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-worker-synthesis --extra runtime --no-default-groups --frozen

ENTRYPOINT ["bash", "scripts/runtime/start-synthesis-worker.sh"]

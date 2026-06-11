# syntax=docker/dockerfile:1.7

ARG PYTHON_BASE_IMAGE=python:3.12-slim-bookworm
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.7.22
ARG PYTORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu

FROM ${UV_IMAGE} AS uv-bin

FROM ${PYTHON_BASE_IMAGE} AS build-base

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

RUN apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 update \
    && apt-get install -y --no-install-recommends bash binutils ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv-bin /uv /uvx /usr/local/bin/

COPY pyproject.toml uv.lock README.md ./
COPY apps ./apps
COPY packages ./packages
COPY workers ./workers
COPY scripts ./scripts
COPY configs ./configs

ARG CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml
ENV CORTEX_RUNTIME_CONFIG_PATH=${CORTEX_RUNTIME_CONFIG_PATH}

RUN <<'SH'
cat >/usr/local/bin/cortex-prune-venv <<'EOF'
#!/usr/bin/env sh
set -eu
venv="${1:-/app/.venv}"

find "$venv" -type d -name __pycache__ -prune -exec rm -rf '{}' +
find "$venv" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.a' \) -delete
EOF

cat >/usr/local/bin/cortex-use-cpu-torch <<'EOF'
#!/usr/bin/env sh
set -eu
venv="${1:-/app/.venv}"
index_url="${PYTORCH_CPU_INDEX_URL:-https://download.pytorch.org/whl/cpu}"

torch_version="$("$venv/bin/python" -c 'import importlib.metadata as m; print(m.version("torch").split("+")[0])' 2>/dev/null || true)"
if [ -z "$torch_version" ]; then
  exit 0
fi

torchvision_version="$("$venv/bin/python" -c 'import importlib.metadata as m; print(m.version("torchvision").split("+")[0])' 2>/dev/null || true)"
if [ -n "$torchvision_version" ]; then
  uv pip install --python "$venv/bin/python" --index-url "$index_url" --reinstall --no-deps \
    "torch==${torch_version}+cpu" "torchvision==${torchvision_version}+cpu"
else
  uv pip install --python "$venv/bin/python" --index-url "$index_url" --reinstall --no-deps \
    "torch==${torch_version}+cpu"
fi

site_packages="$("$venv/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
rm -rf "${site_packages}"/nvidia "${site_packages}"/nvidia-* "${site_packages}"/nvidia_*
rm -rf "${site_packages}"/triton "${site_packages}"/triton-* "${site_packages}"/triton_*
rm -rf "${site_packages}"/cuda "${site_packages}"/cuda-* "${site_packages}"/cuda_*
rm -rf "${site_packages}"/torch/include "${site_packages}"/torch/share
rm -rf "${site_packages}"/torch/test
if [ -d "${site_packages}/torch/bin" ]; then
  find "${site_packages}/torch/bin" -maxdepth 1 -type f \( \
      -name 'test_*' -o \
      -name '*StoreTest' -o \
      -name 'protoc*' \
    \) -delete
fi
"$venv/bin/python" -c 'import torch; print("[cortex] torch", torch.__version__, "cuda", torch.cuda.is_available())'
EOF

cat >/usr/local/bin/cortex-install-db-migrations <<'EOF'
#!/usr/bin/env sh
set -eu
venv="${1:-/app/.venv}"
db_package_root="$("$venv/bin/python" -c 'from pathlib import Path; import cortex_db; print(Path(cortex_db.__file__).resolve().parents[2])')"

rm -rf "${db_package_root}/migrations"
cp /app/packages/db/alembic.ini "${db_package_root}/alembic.ini"
cp -r /app/packages/db/migrations "${db_package_root}/migrations"
find "${db_package_root}/migrations" -type d -name __pycache__ -prune -exec rm -rf '{}' +
find "${db_package_root}/migrations" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
EOF

chmod +x /usr/local/bin/cortex-prune-venv /usr/local/bin/cortex-use-cpu-torch /usr/local/bin/cortex-install-db-migrations
SH

FROM build-base AS api-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-api --no-default-groups --frozen --no-editable \
    && cortex-install-db-migrations /app/.venv \
    && cortex-prune-venv /app/.venv

FROM build-base AS parse-worker-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-worker-parse --no-default-groups --frozen --no-editable \
    && cortex-install-db-migrations /app/.venv \
    && cortex-prune-venv /app/.venv

FROM build-base AS parse-worker-docling-builder
ARG PYTORCH_CPU_INDEX_URL
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-parse --extra docling --no-default-groups --frozen --no-editable \
    && uv pip install --python /app/.venv/bin/python --no-deps ./workers/parse-worker \
    && cortex-install-db-migrations /app/.venv \
    && cortex-use-cpu-torch /app/.venv \
    && cortex-prune-venv /app/.venv

FROM build-base AS knowledge-worker-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-worker-knowledge --no-default-groups --frozen --no-editable \
    && cortex-install-db-migrations /app/.venv \
    && cortex-prune-venv /app/.venv

FROM build-base AS evaluation-worker-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-worker-evaluation --no-default-groups --frozen --no-editable \
    && cortex-install-db-migrations /app/.venv \
    && cortex-prune-venv /app/.venv

FROM build-base AS evaluation-worker-runtime-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-worker-evaluation --extra runtime --no-default-groups --frozen --no-editable \
    && cortex-install-db-migrations /app/.venv \
    && cortex-prune-venv /app/.venv

FROM build-base AS synthesis-worker-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-worker-synthesis --no-default-groups --frozen --no-editable \
    && cortex-install-db-migrations /app/.venv \
    && cortex-prune-venv /app/.venv

FROM build-base AS synthesis-worker-runtime-builder
ARG PYTORCH_CPU_INDEX_URL
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python "$(command -v python)" --package cortex-worker-synthesis --extra runtime --no-default-groups --frozen --no-editable \
    && cortex-install-db-migrations /app/.venv \
    && cortex-use-cpu-torch /app/.venv \
    && cortex-prune-venv /app/.venv

FROM ${PYTHON_BASE_IMAGE} AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml \
    PATH=/app/.venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin

WORKDIR /app

RUN apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/runtime ./scripts/runtime
COPY configs ./configs

FROM runtime-base AS browser-runtime-base

ENV CORTEX_PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT=120000

RUN apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 update \
    && apt-get install -y --no-install-recommends \
      fonts-liberation \
      libasound2 \
      libatk-bridge2.0-0 \
      libatk1.0-0 \
      libcairo2 \
      libcups2 \
      libdbus-1-3 \
      libdrm2 \
      libexpat1 \
      libfontconfig1 \
      libgbm1 \
      libglib2.0-0 \
      libnspr4 \
      libnss3 \
      libpango-1.0-0 \
      libx11-6 \
      libx11-xcb1 \
      libxcb1 \
      libxcomposite1 \
      libxdamage1 \
      libxext6 \
      libxfixes3 \
      libxkbcommon0 \
      libxrandr2 \
      libxrender1 \
      libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

FROM browser-runtime-base AS playwright-browser-assets
ARG CORTEX_PREPARE_CRAWL4AI_RUNTIME=1
COPY --from=uv-bin /uv /uvx /usr/local/bin/
RUN mkdir -p /ms-playwright \
    && if [ "${CORTEX_PREPARE_CRAWL4AI_RUNTIME}" = "1" ]; then \
      uv venv --python "$(command -v python)" /tmp/playwright-venv; \
      uv pip install --python /tmp/playwright-venv/bin/python --no-deps \
        "greenlet==3.4.0" \
        "playwright==1.58.0" \
        "pyee==13.0.1"; \
      /tmp/playwright-venv/bin/python -m playwright install --only-shell chromium; \
    fi \
    && rm -rf /tmp/playwright-venv /ms-playwright/chromium-* /var/lib/apt/lists/* /tmp/*

FROM browser-runtime-base AS api
ARG CORTEX_PREPARE_CRAWL4AI_RUNTIME=1
ARG CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml
ENV CORTEX_RUNTIME_CONFIG_PATH=${CORTEX_RUNTIME_CONFIG_PATH}
COPY --from=playwright-browser-assets /ms-playwright /ms-playwright
COPY --from=api-builder /app/.venv /app/.venv
RUN if [ "${CORTEX_PREPARE_CRAWL4AI_RUNTIME}" = "1" ]; then \
      /app/.venv/bin/python -c 'from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); b.close(); p.stop()'; \
    fi \
    && rm -rf /ms-playwright/chromium-* /var/lib/apt/lists/* /tmp/*
EXPOSE 8080
ENTRYPOINT ["bash", "scripts/runtime/start-api.sh"]

FROM browser-runtime-base AS parse-worker
ARG CORTEX_PREPARE_CRAWL4AI_RUNTIME=1
ARG CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml
ENV CORTEX_RUNTIME_CONFIG_PATH=${CORTEX_RUNTIME_CONFIG_PATH}
COPY --from=playwright-browser-assets /ms-playwright /ms-playwright
COPY --from=parse-worker-builder /app/.venv /app/.venv
RUN if [ "${CORTEX_PREPARE_CRAWL4AI_RUNTIME}" = "1" ]; then \
      /app/.venv/bin/python -c 'from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); b.close(); p.stop()'; \
    fi \
    && rm -rf /ms-playwright/chromium-* /var/lib/apt/lists/* /tmp/*
ENTRYPOINT ["bash", "scripts/runtime/start-parse-worker.sh"]

FROM runtime-base AS parse-worker-docling
ARG CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.docling.yaml
ENV CORTEX_RUNTIME_CONFIG_PATH=${CORTEX_RUNTIME_CONFIG_PATH}
COPY --from=parse-worker-docling-builder /app/.venv /app/.venv
ENTRYPOINT ["bash", "scripts/runtime/start-parse-worker.sh"]

FROM runtime-base AS knowledge-worker
ARG CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml
ENV CORTEX_RUNTIME_CONFIG_PATH=${CORTEX_RUNTIME_CONFIG_PATH}
COPY --from=knowledge-worker-builder /app/.venv /app/.venv
ENTRYPOINT ["bash", "scripts/runtime/start-knowledge-worker.sh"]

FROM runtime-base AS evaluation-worker
ARG CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml
ENV CORTEX_RUNTIME_CONFIG_PATH=${CORTEX_RUNTIME_CONFIG_PATH}
COPY --from=evaluation-worker-builder /app/.venv /app/.venv
ENTRYPOINT ["bash", "scripts/runtime/start-evaluation-worker.sh"]

FROM runtime-base AS evaluation-worker-runtime
ARG CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml
ENV CORTEX_RUNTIME_CONFIG_PATH=${CORTEX_RUNTIME_CONFIG_PATH}
COPY --from=evaluation-worker-runtime-builder /app/.venv /app/.venv
ENTRYPOINT ["bash", "scripts/runtime/start-evaluation-worker.sh"]

FROM runtime-base AS synthesis-worker
ARG CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml
ENV CORTEX_RUNTIME_CONFIG_PATH=${CORTEX_RUNTIME_CONFIG_PATH}
COPY --from=synthesis-worker-builder /app/.venv /app/.venv
ENTRYPOINT ["bash", "scripts/runtime/start-synthesis-worker.sh"]

FROM runtime-base AS synthesis-worker-runtime
ARG CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml
ENV CORTEX_RUNTIME_CONFIG_PATH=${CORTEX_RUNTIME_CONFIG_PATH}
COPY --from=synthesis-worker-runtime-builder /app/.venv /app/.venv
ENTRYPOINT ["bash", "scripts/runtime/start-synthesis-worker.sh"]

# cortex

Vendor-neutral APIs for parsing content, storing files, and operating knowledge pipelines. / 面向内容解析、文件存储与知识流水线的厂商中立 API。

## Workspace

This repository is organized as a `uv` workspace with separate members for:

- `apps/api`
- `workers/parse-worker`
- `workers/knowledge-worker`
- `packages/*`

The repository-level `pyproject.toml` owns dependency groups, lint/type/test settings, and the
shared lockfile.

## Local Development

1. Install Python `3.12`.
2. Copy `.env.example` to `.env` and adjust local settings.
3. Run:

```bash
uv sync --all-packages
uv run --package cortex-api cortex-api
```

Useful checks:

```bash
uv run --group lint ruff check .
uv run --group types pyright
uv run --group test pytest
```

## Specs

Core design documents live under [`specs/`](./specs):

- `cortex-api.yaml`
- `cortex-dfd.md`
- `cortex-prd.md`
- `cortex-schema.md`
- `cortex-tech.md`
- `cortex-tasks.md`
- `cortex-log.md`

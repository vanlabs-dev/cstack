# syntax=docker/dockerfile:1.7
# cstack signalguard-api: FastAPI HTTP surface + cstack CLI in one image.
# Both share the same Python environment so the compose bootstrap services
# can reuse this image to run cstack CLI subcommands (fixtures load,
# audit run, anomaly train) before the api process starts.

FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

WORKDIR /app

# Workspace metadata + lockfile separately so dependency resolution
# is cached when only source files change.
COPY pyproject.toml uv.lock ./

# Workspace member sources. uv reads the entire workspace graph at sync
# time, so every member's pyproject.toml must be present.
COPY packages/ ./packages/
COPY apps/signalguard-api/ ./apps/signalguard-api/
COPY apps/cstack-cli/ ./apps/cstack-cli/

# Sync the whole workspace (--no-dev skips test deps). Per-package syncs
# clobber each other's editable installs, so we install the full graph
# once. The api image hosts both the FastAPI surface and the cstack CLI;
# the compose bootstrap services reuse the same image to run CLI
# subcommands before the api process starts.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --all-packages


FROM python:3.12-slim AS runtime

# Non-root runtime user. /data is the persistent surface bind-mounted by
# Compose; owning it here keeps DuckDB and MLflow SQLite writes from
# tripping over root-owned bind-mount roots on first up.
RUN groupadd --system --gid 1001 cstack && \
    useradd --system --uid 1001 --gid cstack --shell /bin/bash --create-home cstack && \
    mkdir -p /data /data/mlruns /data/raw && \
    chown -R cstack:cstack /data

WORKDIR /app
COPY --from=builder --chown=cstack:cstack /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    SIGNALGUARD_API_DB_PATH=/data/cstack.duckdb \
    MLFLOW_TRACKING_URI=sqlite:////data/mlruns/mlflow.sqlite

USER cstack

EXPOSE 8000

# Module-level entrypoint avoids issues with cli console scripts under
# uv-managed entry-point shims when invoked as a subcommand.
CMD ["python", "-m", "uvicorn", "signalguard_api.main:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8000"]

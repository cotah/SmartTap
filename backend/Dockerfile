FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv==0.5.13

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app

EXPOSE 8000

# Exec-form CMD with `sh -c` so ${PORT} gets expanded at runtime AND signals
# propagate cleanly. Railway and Fly inject the port via the PORT env var;
# locally we fall back to 8000 so `docker run -p 8000:8000 …` keeps working
# without extra flags. The `exec` before `uv run` replaces the shell with
# the uv process so SIGTERM from the orchestrator reaches it directly
# (without `exec`, sh would catch the signal and the container would hang
# until Railway force-kills it on redeploy).
CMD ["sh", "-c", "exec uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

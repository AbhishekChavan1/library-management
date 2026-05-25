# ── Build stage ──
FROM ghcr.io/astral-sh/uv:python3.11-bookworm AS builder
WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen

# ── Runtime stage ──
FROM python:3.11-slim
WORKDIR /app

RUN useradd -m -u 1000 appuser

COPY --from=builder /app/.venv /app/.venv
COPY --chown=appuser:appuser . .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

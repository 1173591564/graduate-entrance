FROM ghcr.io/astral-sh/uv:0.7.19 AS uv

FROM python:3.11.12-slim-bookworm

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
COPY backend/src ./src
COPY seed/syllabus/raw ./seed/syllabus/raw
RUN uv sync --frozen --no-dev

RUN mkdir -p /app/data/problem-images \
    && useradd --create-home --uid 10001 app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && uv run --no-sync python -m graduate_entrance.syllabus.importer && exec uv run --no-sync uvicorn graduate_entrance.main:app --host 0.0.0.0 --port 8000"]

# Backend

FastAPI service for the 11408 graduate entrance preparation system.

## Commands

```bash
uv sync --all-groups
uv run uvicorn graduate_entrance.main:app --reload
uv run ruff check .
uv run mypy src
uv run pytest
```

Copy `.env.example` to `.env` when running outside Docker Compose.

# Backend

FastAPI service for the 11408 graduate entrance preparation system.

## Commands

```bash
uv sync --all-groups
uv run uvicorn graduate_entrance.main:app --reload
uv run ruff check .
uv run mypy src
uv run pytest
uv run alembic upgrade head
uv run python -m graduate_entrance.syllabus.importer
```

Copy `.env.example` to `.env` when running outside Docker Compose.

The importer reads the four versioned CSV files from `../seed/syllabus/raw`. It uses deterministic
identifiers, so repeated imports update the same records instead of creating duplicates.

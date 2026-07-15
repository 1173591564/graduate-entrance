# Contributing

## Workflow

1. Branch from `main` using a short `devin/...` or feature branch name.
2. Keep changes scoped to one vertical slice.
3. Run the relevant quality checks before opening a pull request.
4. Never commit credentials, `.env` files, database backups or user uploads.

## Quality checks

### Backend

```bash
cd backend
uv sync --all-groups
uv run ruff check .
uv run mypy src tests
uv run pytest
```

### Web

```bash
cd web
npm install
npm run lint
npm run typecheck
npm run test
npm run build
```

### Android

```bash
cd android
./gradlew lint testDebugUnitTest assembleDebug
```

### Infrastructure

```bash
docker compose config
docker compose up --build
```

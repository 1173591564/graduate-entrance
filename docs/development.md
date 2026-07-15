# Development

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

The example token is local-development only. Replace `APP_API_TOKEN` before exposing the service.

- Web: `http://localhost:8080`
- API documentation: `http://localhost:8000/api/docs`
- Planning configuration: `http://localhost:8080/planning`
- PostgreSQL: `localhost:5432`

Stop the stack with `docker compose down`. Add `--volumes` only when intentionally deleting local
database data.

## Backend

The backend requires Python 3.11 and uv.

```bash
cd backend
cp .env.example .env
uv python install 3.11
uv sync --all-groups
uv run alembic upgrade head
uv run python -m graduate_entrance.syllabus.importer
uv run uvicorn graduate_entrance.main:app --reload
```

Docker Compose applies migrations and performs the idempotent syllabus import automatically.
Protected API routes require `Authorization: Bearer <APP_API_TOKEN>`. Liveness and readiness remain
public for container orchestration.

Regenerate the committed OpenAPI contract and Web types after changing routes or schemas:

```bash
cd backend
uv run python -m graduate_entrance.openapi > ../web/openapi.json
cd ../web
npm run generate:api
```

## Web

```bash
cd web
cp .env.example .env
npm install
npm run dev
```

Vite proxies `/api` to the backend at `http://localhost:8000`.

## Android

Set `ANDROID_HOME` to an SDK containing platform 35, then run:

```bash
cd android
./gradlew -PAPI_TOKEN=local-development-only assembleDebug
```

The emulator API base URL is `http://10.0.2.2:8000/`.

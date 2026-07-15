# Development

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

- Web: `http://localhost:8080`
- API documentation: `http://localhost:8000/api/docs`
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

## Web

```bash
cd web
npm install
npm run dev
```

Vite proxies `/api` to the backend at `http://localhost:8000`.

## Android

Set `ANDROID_HOME` to an SDK containing platform 35, then run:

```bash
cd android
./gradlew assembleDebug
```

The emulator API base URL is `http://10.0.2.2:8000/`.

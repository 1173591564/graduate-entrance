# Architecture

## Components

- **Backend:** FastAPI application with SQLAlchemy and Alembic.
- **Database:** PostgreSQL 16 with the pgvector extension.
- **Web:** Vue 3 single-page application served by Caddy.
- **Android:** Kotlin and Jetpack Compose client with Room, Retrofit and WorkManager baselines.
- **Gateway:** Caddy serves the Web application and proxies `/api` to FastAPI.

## Repository layout

```text
backend/              FastAPI service, migrations and tests
web/                  Vue application and component tests
android/              Android application and Gradle wrapper
infra/                Database initialization and infrastructure files
seed/syllabus/raw/    Versioned source syllabus CSV files
docs/product/         Product design and implementation assessment
docs/reference/       Web and Android visual references
```

## Intended backend boundaries

Business slices will be grouped under API, domain, application and persistence boundaries. Scheduler,
AI gateway, retrieval and code execution integrations will remain behind explicit interfaces so the
deterministic study workflow does not depend on external AI availability.

## Data and synchronization

PostgreSQL is the source of truth. Android will persist local state in Room and send immutable,
idempotent events to the API. Conflict and merge rules will be defined before offline synchronization
is implemented.

## Security baseline

- Configuration is supplied through environment variables.
- Database and backend ports bind to loopback in the development Compose file.
- Production credentials, backups and uploads are excluded from Git.
- Code execution will be isolated from the API and database networks when introduced.

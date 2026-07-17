---
name: testing-mastery-loop
description: Test the kp_mastery closed loop end-to-end — Today priority ranking, check-in mastery write-back, mastery gaps API, and weekly retro gap suggestions.
---

# Testing the mastery closed loop

## Devin Secrets Needed

None for local testing. The backend's local default bearer token lives in
`backend/src/graduate_entrance/core/config.py` (`api_token` default). Do not print real
production tokens in evidence.

## Setup

1. `docker compose up -d database`, then `cd backend && uv run alembic upgrade head`.
2. Import the syllabus so knowledge points exist:
   `uv run python -m graduate_entrance.syllabus.importer` (~641 KPs, 2 exam blueprints).
3. Start the backend: `uv run uvicorn graduate_entrance.main:app --port 8000`.
4. Start the web dev server WITH the token, or UI requests will 401:
   `VITE_API_TOKEN=<local token> npm run dev -- --port 8080 --host 127.0.0.1`.
   The Vite proxy does not inject auth; only `VITE_API_TOKEN` does.
5. Seed a minimal planning fixture via API: one phase with subject ratios summing to 100,
   one availability period covering the test dates (rules must list weekdays 0–6 exactly
   once), one reading task template per subject, then
   `POST /api/planning/task-pool/generate` and `POST /api/plan/generate`.
6. Pick a date with exactly two planned tasks from different subjects so the priority
   ranking difference (requirement level → target) is visible.

## Pitfalls that might bite

- `GET /api/mastery/gaps` defaults to `recompute=true`, which persists rows for ALL KPs.
  If you want to prove "signal-alone" persistence, call it with `recompute=false` and start
  from an empty `kp_mastery` table (`DELETE FROM kp_mastery;` on the test DB), otherwise
  `knowledge_point_total` will be 641 instead of just the signaled KPs.
- The retro service recomputes gaps itself, so retro suggestions work even with an empty
  persisted table.
- Reloading the Today page resets the date picker to the real today; re-enter the fixture
  date and click 查看 to verify persistence for other dates.
- Chrome's date input accepts a full `MM/DD/YYYY` string typed after a single click.
- Expected values: one 60-min check-in on an application-level KP gives mastery 75
  (50 studied base + 25 no-review bonus) against target 76; its gap (1.0) drops it out of
  the retro top-3, which is a strong exclusion assertion.

## Recorded flow

1. Today page: assert cross-subject task order matches `priority_score` from
   `GET /api/today?date=...` (higher requirement level ranks first).
2. Check in the top task with a non-default minute value; assert summary updates and the
   completed card sinks below planned cards; reload and re-verify.
3. Swagger `/api/docs`: Authorize with the bearer token, run
   `GET /api/mastery/gaps?limit=5&recompute=false`; assert only signaled KPs are present
   with `studied: true` and the expected mastery/target.
4. Swagger `GET /api/retro?week_start=<monday>`; assert `gap_suggestions` has exactly 3
   diff-style entries sorted by gap desc and excludes the checked-in KP.

## Known UI gaps (as of PRs #46–#49)

The web Today view does not display `priority_score` / `due_review_count` numbers and the
Retro view does not render `gap_suggestions`; ordering is the only UI-visible effect, so
API-level verification through Swagger is required for the rest. These might be added
later — re-check the views before assuming.

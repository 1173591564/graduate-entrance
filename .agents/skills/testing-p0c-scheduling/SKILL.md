---
name: testing-p0c-scheduling
description: Test deterministic task-pool generation, plan preview and persistence, calendar summaries, and completed-task preservation end-to-end.
---

# Testing deterministic scheduling

## Devin Secrets Needed

None for local Docker Compose testing through Caddy. If calling the backend port directly, use the
repository's `API_TOKEN` secret without printing it in evidence.

## Setup

1. Rebuild the current source with `docker compose up -d --build`.
2. Wait until database, backend, and Web are healthy in `docker compose ps`.
3. Prepare an isolated planning fixture with:
   - at least two subjects and multiple knowledge points;
   - active task templates that expand into more work than the weekly target;
   - daily availability, a weekly target, subject ratios, and a knowledge dependency.
4. Record fixture IDs and expected capacity values outside the browser recording.
5. Open `http://127.0.0.1:8080/api/docs` in the existing Chrome window.

## Recorded Swagger flow

1. Execute `POST /api/planning/task-pool/generate` twice.
   - First execution should create the expected items.
   - Second execution should make no changes and keep the same total.
2. Execute `GET /api/planning/task-pool` and verify the total and distinct items.
3. Execute `POST /api/plan/preview` twice with the same date range.
   - Verify the response is not persisted.
   - Verify daily and weekly capacity, subject ratios, dependency order, and overflow warnings.
4. Execute `POST /api/plan/generate` with the same request.
   - Verify the response is persisted and the generated task/day totals match the preview.
5. Execute `GET /api/calendar?month=YYYY-MM`.
   - Verify generated tasks appear on their planned dates and weekly totals match the plan.
6. Add consolidated structured recording annotations for task-pool idempotency, deterministic
   preview, persistence, calendar totals, and completed-task preservation.

## Exact deterministic checks

Fetch both preview responses through the Caddy `/api` path, canonicalize them with `jq -S`, and use
`cmp` to require exact equality. Also assert:

- every scheduled task fits daily availability;
- total planned minutes do not exceed the weekly target;
- subject planned minutes follow configured ratios;
- dependency predecessors sort before successors by `(planned_date, order)`;
- the overflow warning count equals the unscheduled pool-item count;
- preview does not create scheduled-task rows.

## Completed-task preservation

1. Persist an initial plan.
2. Mark the earliest task completed with a non-default `actual_minutes` value and retain its ID/date.
3. Add a zero-minute availability exception for that date.
4. Generate the same date range again.
5. Verify the completed task keeps its ID, date, status, and actual minutes.
6. Verify the calendar contains it exactly once and both day/week completed-minute summaries include
   its actual minutes.

## Evidence and cleanup

- Capture full-screen screenshots for first/second generation, preview ratios and warning,
  persisted plan, calendar totals, and completed-task preservation.
- Put expected and actual values plus canonical comparison results in `test-report.md`.
- Post one PR comment containing the key screenshots and a link to the Devin session.
- Remove the isolated fixture and verify task-pool and scheduled-task counts return to their clean
  starting state.

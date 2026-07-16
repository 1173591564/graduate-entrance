---
name: testing-today-checkin
description: Test the dated Today page, actual-minute check-in, retry idempotency, and calendar aggregation end-to-end.
---

# Testing Today task check-ins

## Devin Secrets Needed

None for local Docker Compose testing through Caddy. Caddy injects the repository's local
development bearer token. Do not expose that token in screenshots, recordings, reports, or logs.

## Setup

1. Rebuild the current source with `docker compose up -d --build`.
2. Wait until database, backend, and Web are healthy in `docker compose ps`.
3. Create an isolated deterministic fixture with at least two planned tasks on one date.
4. Generate the task pool and persist the plan before recording.
5. Record the expected planned minutes, initial completed minutes, and remaining minutes.

## Recorded Web flow

1. Open the Web home page and use the header's **今日任务** link.
2. Select the fixture date and click **查看**.
   - Chrome's native date control might be segmented. If direct full-value entry fails, enter
     month, day, and year segments individually rather than using page-level select-all.
3. Verify task titles, subjects, planned duration, completed duration, remaining duration, and
   task-count progress against the fixture.
4. Change one task's actual minutes and click **完成打卡**.
5. Verify the confirmation, completed card, summary changes, and removal of that card's button.
6. Reload the selected date through **查看** and verify the completed state remains.
7. Add consolidated setup, test-start, precondition, mutation, and persistence annotations.

## Exact retry and integration checks

1. Read `/api/today?date=YYYY-MM-DD` through Caddy and capture the completed task ID and `done_at`.
2. POST the same `{"actual_minutes": N}` body to `/api/tasks/{id}/done` twice.
3. Canonicalize both responses with `jq -S` and require exact equality with `cmp`.
4. Verify `done_at` remains unchanged, status remains `completed`, and actual minutes remain `N`.
5. Read Today again and verify:
   - planned minutes still sum non-skipped estimates;
   - completed minutes sum actual minutes;
   - remaining minutes sum only planned estimates.
6. Read the matching calendar month and verify the completed minutes appear once in both day and
   week summaries.

## Evidence and cleanup

- Capture full-screen before and after screenshots.
- Put screenshots inline in `test-report.md` and attach the annotated recording.
- Post one PR comment with the key visual evidence and exact runtime assertions.
- Remove the isolated fixture and verify its task-pool and scheduled-task counts return to zero.

---
name: testing-reschedule-leave
description: Test carry-over rescheduling (顺延), one-click reschedule-from-date, and leave-day mode end-to-end via the Web Today page. Use when verifying /api/plan/reschedule or Today-page reschedule/leave UI changes.
---

# Testing reschedule + leave mode

## Devin Secrets Needed

None for local Docker Compose testing through Caddy (`http://127.0.0.1:8080`).

## Setup

1. `docker compose up -d --build` from the repo root; wait until all services are healthy.
2. Seed an isolated fixture directly in Postgres (via the backend venv's SQLAlchemy models):
   two subjects × two knowledge points, one phase covering a ~1-week future window, availability
   rules (e.g. 120 min/day, weekly target 240), and one active reading template per subject.
   - Flush subjects before dependent rows; SQLAlchemy's topological sort may otherwise insert
     task_templates first and hit an FK violation.
   - On Windows, set `PYTHONIOENCODING=utf-8` before printing Chinese titles from scripts.
3. `POST /api/planning/task-pool/generate`, then `POST /api/plan/generate` for the phase range so
   tasks land on the first days of the window.
   - PowerShell tip: write JSON bodies to a file (`Set-Content -Encoding ascii`) and use
     `curl.exe --data "@body.json"` — inline quoting mangles JSON.

## Recorded UI flow (Today page)

1. Open `http://127.0.0.1:8080/today`. If typing URLs in the address bar drops `:` characters,
   launch via `Start-Process "chrome" "http://127.0.0.1:8080/today"` instead.
2. Set 查看日期 to a mid-window date after the seeded tasks (type digits like `08052026` into the
   native date input after clicking its month segment), click 查看 — expect no tasks (precondition).
3. Click 「一键从当前日期重排」 — expect a notice `已从 <start> 重排至 <end>，顺延 N 项任务` where N equals
   the count of planned tasks dated before the selected date, and tasks now show 「已顺延 1 次」.
4. Click 「请假并重排」 — expect the selected day to become empty (计划 0 分钟) and the following days to
   absorb the tasks. Note: `carried_over` only counts tasks dated **before** start_date, so the
   leave-day notice may legitimately say 顺延 0 项.
5. Complete one task (打卡 with a non-default 实际耗时), reschedule again, and verify the completed
   task keeps its date/minutes.

## Shell assertions

- DB snapshot of `scheduled_tasks`: after reschedule, all tasks are ≥ start_date with
  `carry_count` incremented once; total count unchanged (no dupes/deletions).
- Idempotency: POST `/api/plan/reschedule` twice with the same `leave_dates` — both HTTP 200
  (no 409), one `availability_exceptions` row per leave date with `available_minutes=0`.
- `GET /api/planning/config` shows the leave exception with reason 请假.

## Cleanup

Delete fixture rows (scheduled_tasks, task_pool_items, task_templates, phases, availability
periods/exceptions, syllabus rows, subjects) keyed by a unique marker string; verify
`scheduled_tasks` count returns to the pre-test value.

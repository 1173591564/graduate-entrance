---
name: testing-problem-review
description: Test the SM-2 review scheduling flow (due deck, grading, draft toggle) end-to-end via the Web /reviews page and API. Use when verifying /api/problems/reviews/* or ReviewsView changes.
---

# Testing SM-2 Problem Review

## Stack
- `cp .env.example .env && docker compose up -d --build` from repo root. Web at http://127.0.0.1:8080, API proxied under `/api` with Bearer token `local-development-only` (local dev only).
- Backend auto-runs migrations + syllabus import on startup; verify with `GET /api/syllabus` (expect ~641 knowledge points).

## Seeding a due review card
All problems get `due_date = today` on creation, so any new problem is immediately due.
1. Create draft: `POST /api/problems` (multipart) with `kind` in `wrong|hard|good` and `content_md` (and optional `image`/`source_ref`).
2. Confirm: `POST /api/problems/{id}/confirm` with JSON `{content_md, kind, knowledge_points:[{knowledge_point_id, role:"primary", weight:1.0}]}` — exactly one primary KP and weights summing to 1 are required.
3. Optional solution: `POST /api/problems/{id}/solutions` with `{content_md, method_tag, source}`.
Get a KP id from `GET /api/syllabus` (KPs may be under chapters directly or under sections).

## Key endpoints
- `GET /api/problems/reviews/due?as_of=&include_drafts=&limit=` — drafts included by default; note the route is registered before `/problems/{id}`.
- `POST /api/problems/{id}/review?as_of=YYYY-MM-DD` body `{"grade":"forgot|vague|mastered"}`.
- `as_of` lets you simulate multi-day SM-2 progression without waiting: mastered → interval 1, then 6, then `round(prev_interval * ef)`; forgot → reps=0/interval=1; EF floor 1.3.

## UI flow (record this part)
- Nav 复习 → `/reviews`: header badge `到期 N`, cards show status badge (草稿/已定稿), 复习次数, 到期 date, KP tags, 显示解法 toggle, and grade buttons 忘了/模糊/掌握.
- Grading removes the card and shows banner `已评级「…」，下次复习 <date>（间隔 N 天）`.
- 包含草稿题 checkbox re-fetches; 刷新 button reloads the deck.
- Chrome address bar may drop `:` when typing full URLs (google search + captcha); typing `127.0.0.1:8080/reviews` and clicking the URL suggestion works.

## Cleanup
`docker compose exec -T database psql -U graduate_entrance -d graduate_entrance -c "DELETE FROM problems;"`

## Devin Secrets Needed
None — local stack uses the checked-in dev token `local-development-only`.

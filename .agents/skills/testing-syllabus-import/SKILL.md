---
name: testing-syllabus-import
description: Test the syllabus import, API tree, Web hierarchy, exam-structure separation, and importer idempotency end-to-end.
---

# Testing the syllabus slice

## Devin Secrets Needed

None for local Docker Compose testing.

## Setup

1. From the repository root, rebuild rather than only restarting:
   `docker compose up -d --build`.
2. Wait until `docker compose ps` reports database, backend, and Web as healthy.
3. Verify the Web bundle under `/srv/assets` was produced by the current source. A stale container
   might preserve old `<details>` behavior even when local source has changed.
4. Open `http://127.0.0.1:8080/` in the existing Chrome window.

## Recorded UI flow

1. Click **查看考纲树** and verify `/syllabus`.
2. Record the aggregate cards and all four subject tabs before expanding content.
3. Expand one math chapter and verify the complete
   `module → chapter → section → knowledge point` hierarchy plus a raw requirement label.
4. Switch to politics and verify its source count differs from its knowledge-point count, its exam
   structure is in the sidebar, and a chapter expands directly to knowledge points without a fake
   section.
5. Switch to English and verify the same exam-structure separation.
6. Use structured recording annotations for totals, hierarchy, politics, and English assertions.

## Runtime contract

Fetch `/api/syllabus` through Caddy and verify:

```text
source_row_count=643
knowledge_point_count=641
exam_blueprint_count=2
versions=4
```

Expected per-subject `(source rows, knowledge points)`:

```text
数学一 (214, 214)
408    (338, 338)
英语一 (31, 30)
政治   (60, 59)
```

## Idempotency

Record counts for `subjects`, `syllabus_modules`, `chapters`, `sections`, `knowledge_points`,
`exam_blueprints`, and `syllabus_versions`. Run:

```bash
docker compose exec -T backend python -m graduate_entrance.syllabus.importer
```

Query the same tables again. Every count must remain unchanged.

## Evidence

- Send one focused annotated recording for the UI flow.
- Capture full-screen screenshots for totals, math hierarchy, politics direct chapter points, and
  English exam structure.
- Put exact API and before/after database counts in `test-report.md`.

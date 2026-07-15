---
name: testing-stage0-contracts
description: Test API authentication, unified errors, request IDs, Web proxy auth, and Android connectivity end-to-end.
---

# Testing Stage 0 contracts

## Devin Secrets Needed

None for local Docker Compose testing. Use `APP_API_TOKEN` for non-local environments; never put its
value in recordings, reports, or committed files.

## Setup

1. Build and start the current source with `docker compose up -d --build`.
2. Wait for database, backend, and Web to report healthy in `docker compose ps`.
3. Build Android with `ANDROID_HOME` pointing to an SDK containing API 35:
   `./gradlew -PAPI_TOKEN=<token> assembleDebug`.
4. For emulator testing, use `graduate-entrance-api35` when available. KVM access might require an
   ACL for the current user; confirm with `emulator -accel-check`.

## Recorded browser flow

1. Open the backend directly at `http://127.0.0.1:8000/api/ping`.
   Verify the unified `unauthorized` envelope includes a non-empty request ID.
2. Open `http://127.0.0.1:8000/api/health/live`.
   Verify it remains public and returns `{"status":"ok"}`.
3. Open `http://127.0.0.1:8080/`.
   Verify `后端已连接`; Caddy should inject the token without exposing it to browser JavaScript.
4. Click `配置学习计划`.
   Verify `/planning` renders all four configuration sections without `规划配置加载失败`.

## Android token-state flow

1. Build/install an APK with an intentionally invalid token and launch
   `com.graduateentrance.app/.MainActivity`; verify `后端未连接`.
2. Build/install the otherwise-identical APK with the Compose token; relaunch and verify
   `后端已连接`.
3. Emulator windows might stay above Chrome. `wmctrl` can move them off-screen during browser
   assertions and restore/activate them for Android assertions.

## Supporting evidence

- Capture unauthenticated ping headers and verify HTTP 401, `WWW-Authenticate: Bearer`, and
  `X-Request-ID`.
- Verify the response-header request ID equals `error.request_id` in the JSON body.
- Capture Caddy `/api/ping` status 200 and backend access logs containing method, path, status,
  duration, and request ID.
- Use full-screen screenshots and one annotated recording; pair invalid/valid Android screenshots
  as before/after evidence.

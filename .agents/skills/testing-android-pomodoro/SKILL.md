---
name: testing-android-pomodoro
description: Test Android app features (e.g. pomodoro timer) end-to-end on a local emulator against the Docker Compose backend. Use when verifying changes under android/ that need runtime UI verification.
---

# Testing the Android app on an emulator

## Devin Secrets Needed

None. The debug APK's default `API_BASE_URL=http://10.0.2.2:8000/` reaches the host backend
(token default `local-development-only`), and host-side API checks go through Caddy at
`http://127.0.0.1:8080/api` without a token.

## Environment setup

1. Backend: `docker compose up -d --build` at repo root; wait until all three containers healthy.
2. Android SDK lives at /home/ubuntu/Android/Sdk (android/local.properties points there). If the
   emulator is missing: `yes | /home/ubuntu/Android/Sdk/cmdline-tools/latest/bin/sdkmanager "emulator" "system-images;android-35;google_apis;x86_64"`.
3. KVM: `/dev/kvm` may not be accessible to ubuntu — run `sudo chmod a+rw /dev/kvm` first or the
   emulator silently exits.
4. Create/start the AVD:
   - `echo no | /home/ubuntu/Android/Sdk/cmdline-tools/latest/bin/avdmanager create avd -n test35 -k "system-images;android-35;google_apis;x86_64" -d pixel_6`
   - `/home/ubuntu/Android/Sdk/emulator/emulator -avd test35 -gpu swiftshader_indirect -no-snapshot -no-audio &`
   - Boot wait: `/home/ubuntu/Android/Sdk/platform-tools/adb wait-for-device; /home/ubuntu/Android/Sdk/platform-tools/adb shell 'while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 2; done'`
5. Build & install: `cd android && ./gradlew :app:assembleDebug` then
   `/home/ubuntu/Android/Sdk/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk`; launch with
   `/home/ubuntu/Android/Sdk/platform-tools/adb shell monkey -p com.graduateentrance.app 1`.
6. Seed Today tasks per testing-p0c-scheduling / testing-today-checkin: create phase +
   availability period covering the host date, task templates (use `default_est_minutes: 1` for a
   quick pomodoro finish), `POST /api/planning/task-pool/generate`, then `POST /api/plan/generate`
   for the target date. The emulator picks up the host date automatically.

## Pitfalls

- Nested virtualization: the emulator can crash mid-session (window disappears, crashpad errors in
  the log). Just relaunch it; app/backend state survives. Keep recordings short.
- Pre-boot QEMU hangs: try at most the normal KVM launch, one clean `-wipe-data` launch, and one
  constrained software launch (`-accel off -cores 1 -memory 1536`). If all fail before
  `sys.boot_completed=1`, stop retrying, preserve the QEMU error lines and empty absolute-path
  `adb devices -l` output, and report every Android UI assertion as untested.
- Emulator clicks are laggy — a tap may need a retry; verify the resulting UI state, not the click.
- Notification checks: `adb shell cmd statusbar expand-notifications` / `collapse` show the shade
  reliably in recordings.
- Dismiss the "nested virtualization" and "compatibility warning" host dialogs (OK button) before
  recording assertions.
- Pomodoro specifics: button label is 专注 min(est,25) 分钟; only one pomodoro can run (other
  buttons grey out); finish auto-checks-in via `/api/tasks/{id}/done` — verify with
  `GET /api/today?date=...` (`status completed`, `actual_minutes`, `done_at`).

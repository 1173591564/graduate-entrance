---
name: testing-android-pomodoro
description: Test Android app features end-to-end on an emulator or authorized physical device against the Docker Compose backend. Use when verifying changes under android/ that need runtime UI verification.
---

# Testing the Android app

## Devin Secrets Needed

- None for a local emulator or locally attached physical device.
- `WINDOWS_TUNNEL_BEARER` only when ADB and Compose are accessed through a user-provided,
  authenticated Windows tunnel.

The emulator debug APK's default `API_BASE_URL=http://10.0.2.2:8000/` reaches the host backend,
and host-side API checks go through Caddy at `http://127.0.0.1:8080/api`.

## Emulator setup

1. Backend: `docker compose up -d --build` at repo root; wait until all three containers healthy.
2. Android SDK lives at /home/ubuntu/Android/Sdk (android/local.properties points there). If the
   emulator is missing: `yes | /home/ubuntu/Android/Sdk/cmdline-tools/latest/bin/sdkmanager "emulator" "system-images;android-35;google_apis;x86_64"`.
3. KVM: the blueprint now adds `ubuntu` to the `kvm` group so the emulator boots accelerated. In an
   older snapshot, if the emulator exits with "This user doesn't have permissions to use KVM", run
   `sudo usermod -aG kvm ubuntu && sudo chmod 666 /dev/kvm` and relaunch via `sg kvm -c "emulator ..."`.
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

## Physical-device fallback

1. Require an authorized device from the absolute SDK path:
   `/home/ubuntu/Android/Sdk/platform-tools/adb devices -l`. Never clear unrelated device data.
2. Route a USB device to the local backend with
   `adb reverse tcp:8000 tcp:8000`, then build with
   `-PAPI_BASE_URL=http://127.0.0.1:8000/`.
3. Install with `adb install -r`. If Android reports `INSTALL_FAILED_UPDATE_INCOMPATIBLE`, first
   look for the original signing key. Uninstall the existing package only after explicit user
   approval because uninstalling clears that app's local data.
4. Launch with `adb shell am start -n com.graduateentrance.app/.MainActivity`. Some OEM devices
   rotate after a `monkey` launch; capture the original rotation settings, lock portrait for the
   test if necessary, and restore them during cleanup.
5. Use repository-owned image fixtures in the system Photo Picker. Put copies in a standard album
   such as `Download` and run a media scan when an OEM picker hides custom directories.
6. Record the phone with `adb shell screenrecord` and pull the finalized MP4s afterward. Native
   phone recordings cannot contain Devin desktop annotations, so pair them with full-screen native
   screenshots and backend postconditions; optionally add an annotated desktop playback while
   retaining the originals.
7. For share intake, visible OEM Gallery/chooser behavior is the primary assertion. If the app is
   absent from the visible chooser, mark that path untested. Handler-only fallback checks may verify
   `ACTION_SEND` separately, but a true `ACTION_SEND_MULTIPLE` must contain a Parcelable URI list
   and `ClipData` grants; command-line string arrays are not equivalent.

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
- Keep device date and backend host date explicit in reports. Review scheduling without an `as_of`
  query uses the backend date, which can differ from a manually configured phone date.

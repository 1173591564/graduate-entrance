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
2. Android SDK location varies by snapshot: check both `/home/ubuntu/Android/Sdk` and
   `/home/ubuntu/android-sdk`. If `android/local.properties` is absent, `export ANDROID_HOME=<sdk path>`
   before running gradle. If emulator/system image are missing:
   `yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager "emulator" "system-images;android-35;google_apis;x86_64"`.
3. KVM: the blueprint may add `ubuntu` to the `kvm` group. If not effective, `sudo chmod 666 /dev/kvm`
   works without re-login.
4. Create/start the AVD:
   - `echo no | $ANDROID_HOME/cmdline-tools/latest/bin/avdmanager create avd -n test35 -k "system-images;android-35;google_apis;x86_64" -d pixel_6`
   - `$ANDROID_HOME/emulator/emulator -avd test35 -gpu swiftshader_indirect -no-snapshot -no-audio &`
   - Boot wait: `adb wait-for-device; adb shell 'while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 2; done'`
   - A SystemUI ANR dialog may appear right after boot; wait ~30 s and it clears on its own (or tap Wait).
5. Build & install: `cd android && ./gradlew :app:assembleDebug` then
   `adb install -r app/build/outputs/apk/debug/app-debug.apk`; launch with
   `adb shell monkey -p com.graduateentrance.app 1`.
6. App settings: in-app 设置 (gear on 首页) already defaults to `http://10.0.2.2:8000/` and token
   `local-development-only`; just tap 保存.
7. Seed Today tasks per testing-p0c-scheduling / testing-today-checkin when testing pomodoro flows.

## Seeding papers + PDF for the 阅读 tab / PDF viewer

- Sync metadata: `POST /api/papers/sync` with body `{"papers":[{"rel_path":"Agents/x.pdf","title":"...","category":"Agents","size_bytes":1000}]}` (key is `papers`, items need `rel_path`).
- Upload a PDF: `curl -F "file=@/tmp/test.pdf;type=application/pdf" .../api/papers/{id}/file`.
  Generate a multi-page PDF with python `reportlab` (`pip install reportlab`).
- Recitation endpoints are `/api/recitations` (plural), e.g. `/api/recitations/stats`; seed
  auto-imports on backend start via APP_RECITATION_SEED_PATH in compose.yaml.

## Capturing fast transient UI states (busy spinners)

Inline button spinners for local-backend requests last <100 ms. To prove them, run an adb
frame-burst in the background before clicking:
`for i in $(seq 1 40); do adb exec-out screencap -p > /tmp/burst_$i.png; done &`
then locate the transition frame by sampling mean pixel color of the button crop with PIL.

## Physical-device fallback

1. Require an authorized device: `adb devices -l`. Never clear unrelated device data.
2. Route a USB device to the local backend with `adb reverse tcp:8000 tcp:8000`, then build with
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
- For pull-to-refresh gestures via computer-use, `left_mouse_down` requires a prior `mouse_move`
  to the start coordinate; drag slowly in 4–5 steps and screenshot while the button is held.

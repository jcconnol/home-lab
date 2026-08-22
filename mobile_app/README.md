# G.R.A.C.E. mobile app

The Flutter app is a native recreation of the authenticated G.R.A.C.E. dashboard. It talks directly to the existing local API for sign-in, chat, system status, smart devices, music, weather, network diagnostics, briefings, memory, image generation, and personality settings. It does not embed the dashboard in a WebView.

On Android it also supplies a home-screen **G.R.A.C.E. lighting** widget with buttons for Bedtime, Wind down, Movie time, and Getting home. Each button applies its layout directly in Home Assistant, without opening the app.

## Build and publish

Install Flutter, then run this from `mobile_app`:

```powershell
flutter create --platforms=android .
flutter pub get
flutter analyze
flutter build apk --release --dart-define-from-file=..\.env
New-Item -ItemType Directory -Force ..\app\web\downloads
Copy-Item .\build\app\outputs\flutter-apk\app-release.apk ..\app\web\downloads\grace-mobile.apk
```

`flutter create` generates Flutter's standard Gradle wrapper and project files. It must be run before applying the Android widget files from this directory if Flutter has not generated them yet; keep the `android/app/src/main` files in source control after that generation.

Open the dashboard’s **Account → Android app** link to download the published APK. The phone and server must be on the same LAN and use HTTPS; install the local certificate before opening the app.

## Direct Home Assistant lighting

The mobile app calls Home Assistant directly for the configured smart switch. The rest of G.R.A.C.E. continues to use `GRACE_SERVER_URL` (or its built-in `https://10.0.0.5:8443` default).

Flutter accepts dotenv files directly as build-time defines, so the command above loads `GRACE_HOME_ASSISTANT_URL`, `GRACE_HOME_ASSISTANT_TOKEN`, `GRACE_SMART_SWITCH_ENTITY_ID`, and `GRACE_SMART_SWITCH_NAME` from the repository `.env`. Do not commit `.env`: a token supplied this way is embedded in the APK. Prefer a Home Assistant token limited to this phone’s lighting use.

After installing, add **G.R.A.C.E. lighting** from the Android widget picker. The widget controls the five current switches directly:

- **Bedtime:** All lights off.
- **Wind down:** Bedroom Main Lightswitch on; all others off.
- **Movie time:** Stair Light on; all others off.
- **Getting home:** Dining Room, Kitchen, Living Room, and Stair Lights on; Bedroom Main Lightswitch off.

The widget receives the same Home Assistant build settings as the Flutter app, so build with `--dart-define-from-file=..\.env` and use a token limited to this phone's lighting use.

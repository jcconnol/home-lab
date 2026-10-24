# G.R.A.C.E. mobile app

The Flutter app is a native recreation of the authenticated G.R.A.C.E. dashboard. It talks to the existing local API for sign-in, chat, system status, smart devices, lighting, music, weather, network diagnostics, briefings, memory, image generation, and personality settings. It does not embed the dashboard in a WebView.

On Android it also supplies a home-screen **G.R.A.C.E. lighting** widget with buttons for Bedtime, Wind down, Movie time, and Getting home. Each button uses the authenticated G.R.A.C.E. API, without opening the app, so it uses the same lights and layouts as the web dashboard.

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

Open the dashboard's **Account → Android app** link to download the published APK. The phone and server must be on the same LAN and use HTTPS; install the local certificate before opening the app.

## Lighting widget

The mobile lighting screen and widget call the G.R.A.C.E. server configured by `GRACE_SERVER_URL` (or its built-in `https://10.0.0.5:8443` default). G.R.A.C.E. then controls Home Assistant, just as it does for the web dashboard. Home Assistant credentials and entity IDs are not embedded in the APK.

Open the app and sign in before using the widget. The app stores its G.R.A.C.E. server address and authenticated session in Android-private app storage for the widget. If the widget asks you to sign in again, open the app and sign in to refresh its session.

The widget controls the five standard light locations through the server:

- **Bedtime:** All lights off.
- **Wind down:** Bedroom Main Lightswitch on; all others off.
- **Movie time:** Stair Light on; all others off.
- **Getting home:** Dining Room, Kitchen, Living Room, and Stair Lights on; Bedroom Main Lightswitch off.

The labels on the widget remain fixed for space, while the server owns the actual Home Assistant entity IDs and layout targets.

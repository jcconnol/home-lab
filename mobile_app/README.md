# G.R.A.C.E. mobile app

The Flutter app loads the same authenticated G.R.A.C.E. dashboard served by this repository, so every dashboard screen and control stays in sync with the server. On Android it also supplies a home-screen widget with the four lighting layouts. Tapping a widget layout opens the signed-in app and applies that layout through the existing dashboard session; it does not copy login credentials into widget storage.

## Build and publish

Install Flutter, then run this from `mobile_app`:

```powershell
flutter create --platforms=android .
flutter pub get
flutter analyze
flutter build apk --release --dart-define=GRACE_SERVER_URL=https://YOUR-SERVER:8443
New-Item -ItemType Directory -Force ..\app\web\downloads
Copy-Item .\build\app\outputs\flutter-apk\app-release.apk ..\app\web\downloads\grace-mobile.apk
```

`flutter create` generates Flutter's standard Gradle wrapper and project files. It must be run before applying the Android widget files from this directory if Flutter has not generated them yet; keep the `android/app/src/main` files in source control after that generation.

Open the dashboard’s **Account → Android app** link to download the published APK. The phone and server must be on the same LAN and use HTTPS; install the local certificate before opening the app.

After installing and signing in, add **G.R.A.C.E. lighting** from the Android widget picker. Each button opens the app and applies its matching layout. Widget labels use the four default layout names; renamed layouts remain available from the Lighting screen.

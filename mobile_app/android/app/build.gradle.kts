import java.util.Base64

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

val dartDefines = (findProperty("dart-defines") as String?)
    ?.split(',')
    ?.associate { encodedDefine ->
        val define = String(Base64.getDecoder().decode(encodedDefine))
        val (name, value) = define.split('=', limit = 2)
        name to value
    }
    ?: emptyMap()

fun androidString(value: String) = value
    .replace("\\", "\\\\")
    .replace("\"", "\\\"")

android {
    namespace = "com.jcconnol.grace_mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    buildFeatures {
        resValues = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.jcconnol.grace_mobile"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName

        // The widget runs without a Flutter engine, so it needs the same
        // Home Assistant settings that are supplied to Dart at build time.
        resValue("string", "grace_home_assistant_url", androidString(dartDefines["GRACE_HOME_ASSISTANT_URL"] ?: ""))
        resValue("string", "grace_home_assistant_token", androidString(dartDefines["GRACE_HOME_ASSISTANT_TOKEN"] ?: ""))
        resValue("string", "grace_smart_switch_entity_id", androidString(dartDefines["GRACE_SMART_SWITCH_ENTITY_ID"] ?: ""))
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}

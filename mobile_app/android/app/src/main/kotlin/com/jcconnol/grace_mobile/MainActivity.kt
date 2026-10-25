package com.jcconnol.grace_mobile

import android.content.Context
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, WIDGET_CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "configureWidget" -> {
                    getSharedPreferences(WIDGET_PREFERENCES, Context.MODE_PRIVATE).edit()
                        .putString("server", call.argument<String>("server").orEmpty().trimEnd('/'))
                        .putString("cookie", call.argument<String>("cookie").orEmpty())
                        .apply()
                    result.success(null)
                }
                "clearWidgetSession" -> {
                    getSharedPreferences(WIDGET_PREFERENCES, Context.MODE_PRIVATE).edit()
                        .remove("cookie")
                        .apply()
                    result.success(null)
                }
                "getStoredSession" -> {
                    val preferences = getSharedPreferences(WIDGET_PREFERENCES, Context.MODE_PRIVATE)
                    result.success(mapOf(
                        "server" to preferences.getString("server", "").orEmpty(),
                        "cookie" to preferences.getString("cookie", "").orEmpty(),
                    ))
                }
                else -> result.notImplemented()
            }
        }
    }

    companion object {
        private const val WIDGET_CHANNEL = "com.jcconnol.grace_mobile/widget"
        private const val WIDGET_PREFERENCES = "grace_widget"
    }
}

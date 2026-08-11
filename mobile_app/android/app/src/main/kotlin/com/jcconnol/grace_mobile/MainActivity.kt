package com.jcconnol.grace_mobile

import android.content.Intent
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var channel: MethodChannel? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "grace_mobile/widget")
        channel!!.setMethodCallHandler { call, result ->
            when (call.method) {
                "initialPreset" -> result.success(intent.getStringExtra(LightingWidgetProvider.EXTRA_PRESET_ID))
                else -> result.notImplemented()
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        intent.getStringExtra(LightingWidgetProvider.EXTRA_PRESET_ID)?.let {
            channel?.invokeMethod("applyPreset", it)
        }
    }
}

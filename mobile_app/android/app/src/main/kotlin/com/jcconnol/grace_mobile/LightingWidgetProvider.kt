package com.jcconnol.grace_mobile

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.RemoteViews
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.security.SecureRandom
import java.util.concurrent.Executors
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.HttpsURLConnection
import javax.net.ssl.SSLContext
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager
import java.security.cert.X509Certificate

class LightingWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        val views = RemoteViews(context.packageName, R.layout.lighting_widget)
        views.setTextViewText(R.id.widget_status, "Ready")
        val buttons = mapOf(
            "bedtime" to R.id.preset_bedtime,
            "wind_down" to R.id.preset_wind_down,
            "movie_time" to R.id.preset_movie_time,
            "getting_home" to R.id.preset_getting_home,
        )
        buttons.forEach { (presetId, viewId) ->
            val pending = pendingIntent(context, ACTION_APPLY_PRESET, presetId, viewId)
            views.setOnClickPendingIntent(viewId, pending)
        }
        val lightButtons = mapOf(
            "switch.bedroom_main_lightswitch" to R.id.light_bedroom,
            "switch.dining_room_light" to R.id.light_dining_room,
            "switch.kitchen_light" to R.id.light_kitchen,
            "switch.living_room_light" to R.id.light_living_room,
            "switch.stair_light" to R.id.light_stair,
        )
        lightButtons.forEach { (entityId, viewId) ->
            views.setOnClickPendingIntent(viewId, pendingIntent(context, ACTION_TOGGLE_LIGHT, entityId, viewId))
        }
        manager.updateAppWidget(ids, views)
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        when (intent.action) {
            ACTION_APPLY_PRESET -> {
                val presetId = intent.data?.lastPathSegment ?: return
                val preset = presets[presetId] ?: return
                runAction(context, "Applying ${preset.name}…", "${preset.name} applied") { applyPreset(context, presetId) }
            }
            ACTION_TOGGLE_LIGHT -> {
                val entityId = intent.data?.lastPathSegment ?: return
                val light = lights[entityId] ?: return
                runAction(context, "Toggling ${light.name}…", "${light.name} toggled") { toggleLight(context, entityId) }
            }
        }
    }

    private fun pendingIntent(context: Context, action: String, id: String, requestCode: Int): PendingIntent {
        val intent = Intent(context, LightingWidgetProvider::class.java)
            .setAction(action)
            .setData(Uri.parse("grace-mobile://lighting/$action/$id"))
        return PendingIntent.getBroadcast(context, requestCode, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    }

    private fun runAction(context: Context, loading: String, success: String, action: () -> Unit) {
        updateStatus(context, loading)
        val pendingResult = goAsync()
        executor.execute {
            try {
                action()
                updateStatus(context, success)
            } catch (error: Exception) {
                updateStatus(context, "Couldn’t apply: ${error.message ?: "unknown error"}".take(96))
            } finally {
                pendingResult.finish()
            }
        }
    }

    private fun applyPreset(context: Context, presetId: String) {
        val url = context.getString(R.string.grace_home_assistant_url).trimEnd('/')
        val token = context.getString(R.string.grace_home_assistant_token)
        val preset = presets[presetId] ?: return
        require(url.isNotEmpty() && token.isNotEmpty()) { "Home Assistant is not configured." }

        callSwitchService(url, token, "turn_off", allLights - preset.lightsOn)
        callSwitchService(url, token, "turn_on", preset.lightsOn)
    }

    private fun toggleLight(context: Context, entityId: String) {
        val url = context.getString(R.string.grace_home_assistant_url).trimEnd('/')
        val token = context.getString(R.string.grace_home_assistant_token)
        require(url.isNotEmpty() && token.isNotEmpty()) { "Home Assistant is not configured." }
        callSwitchService(url, token, "toggle", setOf(entityId))
    }

    private fun callSwitchService(url: String, token: String, service: String, entityIds: Set<String>) {
        if (entityIds.isEmpty()) return

        val connection = (URL("$url/api/services/switch/$service").openConnection() as HttpURLConnection)
        try {
            if (connection is HttpsURLConnection) {
                connection.sslSocketFactory = localSslSocketFactory
                connection.hostnameVerifier = HostnameVerifier { _, _ -> true }
            }
            connection.requestMethod = "POST"
            connection.connectTimeout = 5_000
            connection.readTimeout = 5_000
            connection.doOutput = true
            connection.setRequestProperty("Authorization", "Bearer $token")
            connection.setRequestProperty("Content-Type", "application/json")
            OutputStreamWriter(connection.outputStream).use { output ->
                output.write("{\"entity_id\":[${entityIds.joinToString(",") { "\"$it\"" }}]}")
            }
            check(connection.responseCode in 200..299) { "Home Assistant request failed." }
        } finally {
            connection.disconnect()
        }
    }

    private fun updateStatus(context: Context, status: String) {
        val views = RemoteViews(context.packageName, R.layout.lighting_widget)
        views.setTextViewText(R.id.widget_status, status)
        val manager = AppWidgetManager.getInstance(context)
        val ids = manager.getAppWidgetIds(ComponentName(context, LightingWidgetProvider::class.java))
        if (ids.isNotEmpty()) manager.partiallyUpdateAppWidget(ids, views)
    }

    companion object {
        private const val ACTION_APPLY_PRESET = "com.jcconnol.grace_mobile.APPLY_PRESET"
        private const val ACTION_TOGGLE_LIGHT = "com.jcconnol.grace_mobile.TOGGLE_LIGHT"
        private val executor = Executors.newSingleThreadExecutor()
        private val localSslSocketFactory by lazy {
            val trustManager = object : X509TrustManager {
                override fun checkClientTrusted(chain: Array<X509Certificate>, authType: String) = Unit
                override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String) = Unit
                override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()
            }
            SSLContext.getInstance("TLS").apply {
                init(null, arrayOf<TrustManager>(trustManager), SecureRandom())
            }.socketFactory
        }
        private val allLights = setOf(
            "switch.bedroom_main_lightswitch",
            "switch.dining_room_light",
            "switch.kitchen_light",
            "switch.living_room_light",
            "switch.stair_light",
        )
        private val presets = mapOf(
            "bedtime" to LightingPreset("Bedtime", emptySet()),
            "wind_down" to LightingPreset("Wind down", setOf("switch.bedroom_main_lightswitch")),
            "movie_time" to LightingPreset("Movie time", setOf("switch.stair_light")),
            "getting_home" to LightingPreset("Getting home", setOf("switch.dining_room_light", "switch.kitchen_light", "switch.living_room_light", "switch.stair_light")),
        )
        private val lights = mapOf(
            "switch.bedroom_main_lightswitch" to LightingLight("Bedroom"),
            "switch.dining_room_light" to LightingLight("Dining room"),
            "switch.kitchen_light" to LightingLight("Kitchen"),
            "switch.living_room_light" to LightingLight("Living room"),
            "switch.stair_light" to LightingLight("Stair light"),
        )
    }
}

private data class LightingPreset(val name: String, val lightsOn: Set<String>)
private data class LightingLight(val name: String)

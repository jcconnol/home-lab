package com.jcconnol.grace_mobile

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.RemoteViews
import java.net.HttpURLConnection
import java.net.URL
import java.security.SecureRandom
import java.security.cert.X509Certificate
import java.util.concurrent.Executors
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.HttpsURLConnection
import javax.net.ssl.SSLContext
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

class LightingWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        val views = RemoteViews(context.packageName, R.layout.lighting_widget)
        views.setTextViewText(R.id.widget_status, "Ready")
        mapOf(
            "bedtime" to R.id.preset_bedtime,
            "wind_down" to R.id.preset_wind_down,
            "movie_time" to R.id.preset_movie_time,
            "getting_home" to R.id.preset_getting_home,
        ).forEach { (presetId, viewId) ->
            views.setOnClickPendingIntent(viewId, pendingIntent(context, ACTION_APPLY_PRESET, presetId, viewId))
        }
        mapOf(
            "bedroom" to R.id.light_bedroom,
            "dining_room" to R.id.light_dining_room,
            "kitchen" to R.id.light_kitchen,
            "living_room" to R.id.light_living_room,
            "stairway" to R.id.light_stair,
        ).forEach { (lightId, viewId) ->
            views.setOnClickPendingIntent(viewId, pendingIntent(context, ACTION_TOGGLE_LIGHT, lightId, viewId))
        }
        manager.updateAppWidget(ids, views)
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        when (intent.action) {
            ACTION_APPLY_PRESET -> {
                val presetId = intent.data?.lastPathSegment ?: return
                val name = presets[presetId] ?: return
                runAction(context, "Applying $name…", "$name applied") {
                    postGrace(context, "/api/lights/presets/$presetId")
                }
            }
            ACTION_TOGGLE_LIGHT -> {
                val lightId = intent.data?.lastPathSegment ?: return
                val name = lights[lightId] ?: return
                runAction(context, "Toggling $name…", "$name toggled") {
                    postGrace(context, "/api/lights/$lightId/toggle")
                }
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

    private fun postGrace(context: Context, path: String) {
        val preferences = context.getSharedPreferences(WIDGET_PREFERENCES, Context.MODE_PRIVATE)
        val url = preferences.getString("server", null)?.trimEnd('/')
            ?: context.getString(R.string.grace_server_url).trimEnd('/')
        val cookie = preferences.getString("cookie", null).orEmpty()
        require(url.isNotEmpty()) { "G.R.A.C.E. server is not configured." }
        require(cookie.isNotEmpty()) { "Open G.R.A.C.E. and sign in first." }

        val connection = URL("$url$path").openConnection() as HttpURLConnection
        try {
            if (connection is HttpsURLConnection) {
                connection.sslSocketFactory = localSslSocketFactory
                connection.hostnameVerifier = HostnameVerifier { _, _ -> true }
            }
            connection.requestMethod = "POST"
            connection.connectTimeout = 5_000
            connection.readTimeout = 8_000
            connection.doOutput = true
            connection.setRequestProperty("Cookie", cookie)
            connection.setRequestProperty("Accept", "application/json")
            connection.outputStream.use { }
            check(connection.responseCode in 200..299) {
                if (connection.responseCode == 401) "Sign in to G.R.A.C.E. again."
                else "G.R.A.C.E. request failed (${connection.responseCode})."
            }
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
        private const val WIDGET_PREFERENCES = "grace_widget"
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
        private val presets = mapOf(
            "bedtime" to "Bedtime",
            "wind_down" to "Wind down",
            "movie_time" to "Movie time",
            "getting_home" to "Getting home",
        )
        private val lights = mapOf(
            "bedroom" to "Bedroom",
            "dining_room" to "Dining room",
            "kitchen" to "Kitchen",
            "living_room" to "Living room",
            "stairway" to "Stair light",
        )
    }
}

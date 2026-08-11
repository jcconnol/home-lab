package com.jcconnol.grace_mobile

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews

class LightingWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        val views = RemoteViews(context.packageName, R.layout.lighting_widget)
        val buttons = mapOf(
            "bedtime" to R.id.preset_bedtime,
            "wind_down" to R.id.preset_wind_down,
            "movie_time" to R.id.preset_movie_time,
            "getting_home" to R.id.preset_getting_home,
        )
        buttons.forEach { (presetId, viewId) ->
            val intent = Intent(context, MainActivity::class.java).putExtra(EXTRA_PRESET_ID, presetId)
            val pending = PendingIntent.getActivity(context, viewId, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            views.setOnClickPendingIntent(viewId, pending)
        }
        AppWidgetManager.getInstance(context).updateAppWidget(ComponentName(context, LightingWidgetProvider::class.java), views)
    }

    companion object {
        const val EXTRA_PRESET_ID = "preset_id"
    }
}

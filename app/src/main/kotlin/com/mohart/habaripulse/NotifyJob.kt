package com.mohart.habaripulse

import android.app.*
import android.app.job.*
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

/** Runs about every 30 min in the background, reads the latest feed and notifies for new "hot" stories. */
class NotifyJob : JobService() {
    override fun onStartJob(p: JobParameters): Boolean {
        thread {
            try { check(applicationContext) } catch (_: Exception) {}
            jobFinished(p, false)
        }
        return true
    }
    override fun onStopJob(p: JobParameters) = true

    companion object {
        private const val CH = "hot"
        private const val JOB_ID = 1

        fun schedule(c: Context) {
            val js = c.getSystemService(Context.JOB_SCHEDULER_SERVICE) as JobScheduler
            if (js.getPendingJob(JOB_ID) != null) return
            js.schedule(
                JobInfo.Builder(JOB_ID, ComponentName(c, NotifyJob::class.java))
                    .setPeriodic(30 * 60 * 1000L)
                    .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
                    .setPersisted(true).build()
            )
        }

        private fun check(c: Context) {
            val url = BuildConfig.FEED_URL
            if (url.isEmpty()) return
            val con = URL(url).openConnection() as HttpURLConnection
            con.connectTimeout = 15000; con.readTimeout = 30000
            if (con.responseCode != 200) return
            val body = con.inputStream.bufferedReader().use { it.readText() }
            val dir = File(c.filesDir, "feed").apply { mkdirs() }
            File(dir, "feed.json").writeText(body)
            val items = JSONObject(body).optJSONArray("items") ?: return
            val prefs = c.getSharedPreferences("notified", Context.MODE_PRIVATE)
            val done = prefs.getStringSet("ids", emptySet())!!.toMutableSet()
            val cutoff = System.currentTimeMillis() / 1000 - 12 * 3600
            var sent = 0
            for (n in 0 until items.length()) {
                val i = items.getJSONObject(n)
                val id = i.optString("id")
                if (!i.optBoolean("hot") || i.optLong("ts") < cutoff || id in done) continue
                if (sent < 3) { notify(c, i); sent++ }
                done.add(id)
            }
            prefs.edit().putStringSet("ids", done.toList().takeLast(500).toSet()).apply()
        }

        private fun notify(c: Context, i: JSONObject) {
            val nm = c.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (Build.VERSION.SDK_INT >= 26)
                nm.createNotificationChannel(NotificationChannel(CH, "Hot stories", NotificationManager.IMPORTANCE_HIGH))
            val open = PendingIntent.getActivity(
                c, i.optString("id").hashCode(),
                Intent(c, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            )
            @Suppress("DEPRECATION")
            val b = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(c, CH) else Notification.Builder(c)
            val summary = i.optString("summary").take(160)
            b.setSmallIcon(R.drawable.ic_stat).setContentTitle(i.optString("title"))
                .setContentText("${i.optString("source")} · $summary")
                .setStyle(Notification.BigTextStyle().bigText("${i.optString("source")}\n$summary"))
                .setContentIntent(open).setAutoCancel(true)
            nm.notify(i.optString("id").hashCode(), b.build())
        }
    }
}

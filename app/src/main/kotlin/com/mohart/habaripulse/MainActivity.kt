package com.mohart.habaripulse

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.webkit.WebViewAssetLoader
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : Activity() {
    private lateinit var web: WebView
    private var lastSync = 0L
    private val host = "appassets.androidplatform.net"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.parseColor("#0b3d2e")
        val dir = File(filesDir, "feed").apply { mkdirs() }
        val loader = WebViewAssetLoader.Builder()
            .setDomain(host)
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .addPathHandler("/feed/", WebViewAssetLoader.InternalStoragePathHandler(this, dir))
            .build()
        web = WebView(this)
        setContentView(web)
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? =
                loader.shouldInterceptRequest(request.url)

            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                if (request.url.host == host) return false
                startActivity(Intent(Intent.ACTION_VIEW, request.url))
                return true
            }
        }
        web.loadUrl("https://$host/assets/index.html")
    }

    override fun onResume() {
        super.onResume()
        if (System.currentTimeMillis() - lastSync > 20 * 60 * 1000) sync()
    }

    private fun sync() {
        val url = BuildConfig.FEED_URL
        if (url.isEmpty()) return
        lastSync = System.currentTimeMillis()
        thread {
            try {
                val c = URL(url).openConnection() as HttpURLConnection
                c.connectTimeout = 15000; c.readTimeout = 30000
                if (c.responseCode == 200) {
                    val dir = File(filesDir, "feed")
                    val tmp = File(dir, "feed.tmp")
                    c.inputStream.use { i -> tmp.outputStream().use { o -> i.copyTo(o) } }
                    tmp.renameTo(File(dir, "feed.json"))
                    web.post { web.evaluateJavascript("window.hpReload&&window.hpReload()", null) }
                }
            } catch (e: Exception) { lastSync = 0 }
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        web.evaluateJavascript("window.hpBack&&window.hpBack()") { r -> if (r != "true") finish() }
    }
}

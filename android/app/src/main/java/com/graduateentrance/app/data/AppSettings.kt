package com.graduateentrance.app.data

import android.content.Context
import android.content.SharedPreferences
import com.graduateentrance.app.BuildConfig

object AppSettings {
    private const val PREFS_NAME = "connection_settings"
    private const val KEY_BASE_URL = "api_base_url"
    private const val KEY_TOKEN = "api_token"

    @Volatile
    private var prefs: SharedPreferences? = null

    fun init(context: Context) {
        if (prefs == null) {
            prefs = context.applicationContext
                .getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        }
    }

    var baseUrl: String
        get() = prefs?.getString(KEY_BASE_URL, null)?.takeIf { it.isNotBlank() }
            ?: BuildConfig.API_BASE_URL
        set(value) {
            prefs?.edit()?.putString(KEY_BASE_URL, normalizeBaseUrl(value))?.apply()
        }

    var token: String
        get() = prefs?.getString(KEY_TOKEN, null)?.takeIf { it.isNotBlank() }
            ?: BuildConfig.API_TOKEN
        set(value) {
            prefs?.edit()?.putString(KEY_TOKEN, value.trim())?.apply()
        }

    private fun normalizeBaseUrl(value: String): String {
        val trimmed = value.trim()
        if (trimmed.isEmpty()) {
            return ""
        }
        val withScheme = if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
            trimmed
        } else {
            "http://$trimmed"
        }
        return if (withScheme.endsWith("/")) withScheme else "$withScheme/"
    }
}

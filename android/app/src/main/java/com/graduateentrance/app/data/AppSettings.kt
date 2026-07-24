package com.graduateentrance.app.data

import android.content.Context
import android.content.SharedPreferences
import com.graduateentrance.app.BuildConfig

object AppSettings {
    private const val PREFS_NAME = "connection_settings"
    private const val KEY_BASE_URL = "api_base_url"
    private const val KEY_TOKEN = "api_token"
    private const val KEY_VOCAB_NEW_LIMIT = "vocab_new_limit"
    const val DEFAULT_VOCAB_NEW_LIMIT = 20
    private const val KEY_READER_FONT_SCALE = "reader_font_scale"
    private const val KEY_READER_THEME = "reader_theme"
    const val DEFAULT_READER_FONT_SCALE = 1.0f
    const val DEFAULT_READER_THEME = "paper"

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

    var vocabNewLimit: Int
        get() = prefs?.getInt(KEY_VOCAB_NEW_LIMIT, DEFAULT_VOCAB_NEW_LIMIT)
            ?: DEFAULT_VOCAB_NEW_LIMIT
        set(value) {
            prefs?.edit()?.putInt(KEY_VOCAB_NEW_LIMIT, value.coerceIn(0, 200))?.apply()
        }

    var readerFontScale: Float
        get() = prefs?.getFloat(KEY_READER_FONT_SCALE, DEFAULT_READER_FONT_SCALE)
            ?: DEFAULT_READER_FONT_SCALE
        set(value) {
            prefs?.edit()?.putFloat(KEY_READER_FONT_SCALE, value.coerceIn(0.8f, 1.6f))?.apply()
        }

    var readerTheme: String
        get() = prefs?.getString(KEY_READER_THEME, DEFAULT_READER_THEME)?.takeIf { it.isNotBlank() }
            ?: DEFAULT_READER_THEME
        set(value) {
            prefs?.edit()?.putString(KEY_READER_THEME, value)?.apply()
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

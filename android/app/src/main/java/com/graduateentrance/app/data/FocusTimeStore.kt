package com.graduateentrance.app.data

import android.content.Context
import android.content.SharedPreferences
import java.time.LocalDate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Accumulated focus minutes per task for today, persisted across restarts. */
object FocusTimeStore {
    private const val PREFS_NAME = "focus_time"

    @Volatile
    private var prefs: SharedPreferences? = null
    private val _minutes = MutableStateFlow<Map<String, Int>>(emptyMap())
    val minutes: StateFlow<Map<String, Int>> = _minutes.asStateFlow()

    fun init(context: Context) {
        if (prefs == null) {
            prefs = context.applicationContext
                .getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            reload()
        }
    }

    fun add(taskId: String, minutes: Int) {
        if (taskId.isBlank() || minutes <= 0) return
        val store = prefs ?: return
        val key = key(taskId)
        store.edit().putInt(key, store.getInt(key, 0) + minutes).apply()
        reload()
    }

    fun clear(taskId: String) {
        prefs?.edit()?.remove(key(taskId))?.apply()
        reload()
    }

    fun minutesFor(taskId: String): Int = _minutes.value[taskId] ?: 0

    private fun key(taskId: String) = "${LocalDate.now()}|$taskId"

    private fun reload() {
        val store = prefs ?: return
        val prefix = "${LocalDate.now()}|"
        val all = store.all
        val stale = all.keys.filterNot { it.startsWith(prefix) }
        if (stale.isNotEmpty()) {
            val editor = store.edit()
            stale.forEach(editor::remove)
            editor.apply()
        }
        _minutes.value = all
            .filterKeys { it.startsWith(prefix) }
            .mapNotNull { (k, v) -> (v as? Int)?.let { k.removePrefix(prefix) to it } }
            .toMap()
    }
}

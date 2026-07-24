package com.graduateentrance.app.data

import android.content.Context
import android.content.SharedPreferences

/** Last-read block index per paper, persisted across restarts. */
object ReadingProgressStore {
    private const val PREFS_NAME = "reading_progress"

    @Volatile
    private var prefs: SharedPreferences? = null

    fun init(context: Context) {
        if (prefs == null) {
            prefs = context.applicationContext
                .getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        }
    }

    fun save(paperId: String, blockIndex: Int) {
        if (paperId.isBlank() || blockIndex < 0) return
        prefs?.edit()?.putInt(paperId, blockIndex)?.apply()
    }

    fun restore(paperId: String): Int = prefs?.getInt(paperId, 0) ?: 0
}

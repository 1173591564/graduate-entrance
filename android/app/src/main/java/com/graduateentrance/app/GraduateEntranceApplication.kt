package com.graduateentrance.app

import android.app.Application
import com.graduateentrance.app.data.AppSettings
import com.graduateentrance.app.data.FocusTimeStore
import com.graduateentrance.app.data.ReadingProgressStore

class GraduateEntranceApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        AppSettings.init(this)
        FocusTimeStore.init(this)
        ReadingProgressStore.init(this)
    }
}

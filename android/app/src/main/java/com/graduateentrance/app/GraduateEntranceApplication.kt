package com.graduateentrance.app

import android.app.Application
import com.graduateentrance.app.data.AppSettings

class GraduateEntranceApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        AppSettings.init(this)
    }
}

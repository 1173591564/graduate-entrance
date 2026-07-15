package com.graduateentrance.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.graduateentrance.app.ui.GraduateEntranceApp
import com.graduateentrance.app.ui.theme.GraduateEntranceTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            GraduateEntranceTheme {
                GraduateEntranceApp()
            }
        }
    }
}

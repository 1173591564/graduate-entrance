package com.graduateentrance.app

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.graduateentrance.app.ui.GraduateEntranceApp
import com.graduateentrance.app.ui.theme.GraduateEntranceTheme

class MainActivity : ComponentActivity() {
    private var sharedUris by mutableStateOf<List<Uri>>(emptyList())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        sharedUris = extractSharedImageUris(intent)
        enableEdgeToEdge()
        setContent {
            GraduateEntranceTheme {
                GraduateEntranceApp(
                    initialCaptureUris = sharedUris,
                    onSharedUrisConsumed = { sharedUris = emptyList() },
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        sharedUris = extractSharedImageUris(intent)
    }

    private fun extractSharedImageUris(intent: Intent?): List<Uri> {
        if (intent == null) {
            return emptyList()
        }
        return when (intent.action) {
            Intent.ACTION_SEND -> {
                extractSingleStream(intent)?.let(::listOf).orEmpty()
            }
            Intent.ACTION_SEND_MULTIPLE -> {
                extractMultipleStreams(intent)
            }
            else -> emptyList()
        }
    }

    private fun extractSingleStream(intent: Intent): Uri? =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent.getParcelableExtra(Intent.EXTRA_STREAM)
        }

    private fun extractMultipleStreams(intent: Intent): List<Uri> =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM, Uri::class.java)
                ?.toList()
                .orEmpty()
        } else {
            @Suppress("DEPRECATION")
            intent.getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM)
                ?.toList()
                .orEmpty()
        }
}

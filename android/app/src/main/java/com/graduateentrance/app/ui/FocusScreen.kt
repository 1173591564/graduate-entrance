package com.graduateentrance.app.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Pause
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material.icons.outlined.Stop
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.graduateentrance.app.timer.PomodoroPhase
import com.graduateentrance.app.timer.PomodoroState

@Composable
fun FocusScreen(
    state: PomodoroState,
    onPause: () -> Unit,
    onResume: () -> Unit,
    onStop: () -> Unit,
    onExit: () -> Unit,
) {
    val paused = state.phase == PomodoroPhase.PAUSED
    BackHandler(onBack = onExit)
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.surface,
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            IconButton(
                onClick = onExit,
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .padding(12.dp),
            ) {
                Icon(Icons.Outlined.Close, contentDescription = "退出专注（暂停计时）")
            }
            Column(
                modifier = Modifier
                    .align(Alignment.Center)
                    .padding(horizontal = 32.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(28.dp),
            ) {
                Text(
                    text = state.taskTitle,
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    text = "%02d:%02d".format(
                        state.remainingSeconds / 60,
                        state.remainingSeconds % 60,
                    ),
                    fontSize = 88.sp,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = if (paused) "已暂停" else "专注中",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    FilledTonalButton(onClick = if (paused) onResume else onPause) {
                        Icon(
                            imageVector = if (paused) {
                                Icons.Outlined.PlayArrow
                            } else {
                                Icons.Outlined.Pause
                            },
                            contentDescription = null,
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(if (paused) "继续" else "暂停")
                    }
                    TextButton(onClick = onStop) {
                        Icon(Icons.Outlined.Stop, contentDescription = null)
                        Spacer(Modifier.width(4.dp))
                        Text("放弃")
                    }
                }
            }
        }
    }
}

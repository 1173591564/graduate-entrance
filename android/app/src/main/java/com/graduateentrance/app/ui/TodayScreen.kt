package com.graduateentrance.app.ui

import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.graduateentrance.app.data.local.TodayTaskEntity
import com.graduateentrance.app.timer.PomodoroPhase
import com.graduateentrance.app.timer.PomodoroService
import com.graduateentrance.app.timer.PomodoroState
import com.graduateentrance.app.timer.PomodoroTimer

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TodayScreen(viewModel: TodayViewModel) {
    val state by viewModel.uiState.collectAsState()
    val pomodoro by PomodoroTimer.state.collectAsState()
    val context = LocalContext.current
    var pendingStart by rememberSaveable { mutableStateOf<String?>(null) }
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { _ ->
        pendingStart?.let { taskId ->
            state.tasks.firstOrNull { it.id == taskId }?.let { task ->
                PomodoroService.start(context, task.id, task.title, pomodoroMinutes(task.estMinutes))
            }
        }
        pendingStart = null
    }

    fun startPomodoro(task: TodayTaskEntity) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            pendingStart = task.id
            permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        } else {
            PomodoroService.start(context, task.id, task.title, pomodoroMinutes(task.estMinutes))
        }
    }

    LaunchedEffect(pomodoro.phase) {
        if (pomodoro.phase == PomodoroPhase.FINISHED) {
            viewModel.refresh()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("今日任务")
                        Text(
                            text = state.date.toString(),
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                actions = {
                    TextButton(onClick = { viewModel.selectDate(state.date.minusDays(1)) }) {
                        Text("前一天")
                    }
                    TextButton(onClick = { viewModel.selectDate(state.date.plusDays(1)) }) {
                        Text("后一天")
                    }
                },
            )
        },
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
            contentPadding = PaddingValues(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            if (state.fromCache) {
                item {
                    NoticeCard("离线模式：显示本地缓存数据")
                }
            }
            if (state.pendingCheckIns > 0) {
                item {
                    NoticeCard("待同步打卡：${state.pendingCheckIns} 条")
                }
            }
            state.notice?.let { notice ->
                item {
                    NoticeCard(notice)
                }
            }
            if (pomodoro.phase != PomodoroPhase.IDLE) {
                item {
                    PomodoroCard(
                        state = pomodoro,
                        onPause = { PomodoroService.pause(context) },
                        onResume = { PomodoroService.resume(context) },
                        onStop = { PomodoroService.stop(context) },
                        onDismiss = {
                            PomodoroTimer.clear()
                            viewModel.refresh()
                        },
                    )
                }
            }
            item {
                SummaryRow(
                    planned = state.plannedMinutes,
                    completed = state.completedMinutes,
                    remaining = state.remainingMinutes,
                )
            }
            if (!state.loading && state.tasks.isEmpty()) {
                item {
                    Text(
                        text = "${state.date} 暂无已排任务",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            items(state.tasks, key = { it.id }) { task ->
                TaskCard(
                    task = task,
                    pomodoroEnabled = !pomodoro.active,
                    onCheckIn = { minutes -> viewModel.checkIn(task.id, minutes) },
                    onStartPomodoro = { startPomodoro(task) },
                )
            }
        }
    }
}

@Composable
private fun NoticeCard(text: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.secondaryContainer,
        ),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(14.dp),
        )
    }
}

@Composable
private fun SummaryRow(planned: Int, completed: Int, remaining: Int) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        SummaryCell("计划", planned, Modifier.weight(1f))
        SummaryCell("已完成", completed, Modifier.weight(1f))
        SummaryCell("剩余", remaining, Modifier.weight(1f))
    }
}

@Composable
private fun SummaryCell(label: String, minutes: Int, modifier: Modifier = Modifier) {
    Card(modifier = modifier) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(label, style = MaterialTheme.typography.labelMedium)
            Text("$minutes 分钟", style = MaterialTheme.typography.titleMedium)
        }
    }
}

private fun pomodoroMinutes(estMinutes: Int): Int =
    if (estMinutes in 1 until PomodoroService.DEFAULT_MINUTES) {
        estMinutes
    } else {
        PomodoroService.DEFAULT_MINUTES
    }

@Composable
private fun PomodoroCard(
    state: PomodoroState,
    onPause: () -> Unit,
    onResume: () -> Unit,
    onStop: () -> Unit,
    onDismiss: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer,
        ),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            if (state.phase == PomodoroPhase.FINISHED) {
                Text("番茄钟完成", style = MaterialTheme.typography.titleMedium)
                Text(
                    text = state.notice ?: "专注 ${state.elapsedMinutes} 分钟",
                    style = MaterialTheme.typography.bodyMedium,
                )
                Button(onClick = onDismiss) {
                    Text("知道了")
                }
            } else {
                val minutes = state.remainingSeconds / 60
                val seconds = state.remainingSeconds % 60
                Text(
                    text = if (state.phase == PomodoroPhase.PAUSED) "番茄钟已暂停" else "番茄钟专注中",
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(state.taskTitle, style = MaterialTheme.typography.bodyMedium)
                Text(
                    text = "%02d:%02d".format(minutes, seconds),
                    style = MaterialTheme.typography.displaySmall,
                )
                LinearProgressIndicator(
                    progress = {
                        if (state.totalSeconds == 0) {
                            0f
                        } else {
                            state.elapsedSeconds.toFloat() / state.totalSeconds
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                )
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    if (state.phase == PomodoroPhase.PAUSED) {
                        Button(onClick = onResume) { Text("继续") }
                    } else {
                        Button(onClick = onPause) { Text("暂停") }
                    }
                    OutlinedButton(onClick = onStop) { Text("放弃") }
                }
            }
        }
    }
}

@Composable
private fun TaskCard(
    task: TodayTaskEntity,
    pomodoroEnabled: Boolean,
    onCheckIn: (Int) -> Unit,
    onStartPomodoro: () -> Unit,
) {
    var minutesInput by rememberSaveable(task.id) { mutableStateOf(task.estMinutes.toString()) }
    val completed = task.status == "completed"

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (completed) {
                MaterialTheme.colorScheme.surfaceContainerLow
            } else {
                MaterialTheme.colorScheme.surfaceContainerHigh
            },
        ),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(task.title, style = MaterialTheme.typography.titleMedium)
            Text(
                text = "${task.subjectName} · ${task.knowledgePointName}",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            val badges = buildList {
                add("预计 ${task.estMinutes} 分钟")
                if (task.carryCount > 0) {
                    add("已顺延 ${task.carryCount} 次")
                }
            }
            Text(
                text = badges.joinToString(" · "),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (completed) {
                Text(
                    text = "已完成 ${task.actualMinutes ?: task.estMinutes} 分钟",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary,
                )
            } else if (task.status == "skipped") {
                Text(
                    text = "已跳过",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    OutlinedTextField(
                        value = minutesInput,
                        onValueChange = { minutesInput = it },
                        label = { Text("实际耗时（分钟）") },
                        singleLine = true,
                        modifier = Modifier.weight(1f),
                    )
                    Button(
                        onClick = {
                            minutesInput.toIntOrNull()?.let { minutes ->
                                if (minutes in 0..1440) {
                                    onCheckIn(minutes)
                                }
                            }
                        },
                        enabled = minutesInput.toIntOrNull()?.let { it in 0..1440 } == true,
                    ) {
                        Text("完成打卡")
                    }
                }
                OutlinedButton(
                    onClick = onStartPomodoro,
                    enabled = pomodoroEnabled,
                ) {
                    Text("番茄钟 ${pomodoroMinutes(task.estMinutes)} 分钟")
                }
            }
        }
    }
}

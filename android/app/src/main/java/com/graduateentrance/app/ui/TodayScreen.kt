package com.graduateentrance.app.ui

import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material.icons.outlined.ChevronLeft
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.EventAvailable
import androidx.compose.material.icons.outlined.Pause
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material.icons.outlined.Restore
import androidx.compose.material.icons.outlined.Stop
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberDatePickerState
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.graduateentrance.app.data.FocusTimeStore
import com.graduateentrance.app.data.local.TodayTaskEntity
import com.graduateentrance.app.timer.PomodoroPhase
import com.graduateentrance.app.timer.PomodoroService
import com.graduateentrance.app.timer.PomodoroState
import com.graduateentrance.app.timer.PomodoroTimer
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Locale

private val dayFormatter = DateTimeFormatter.ofPattern("M月d日 EEEE", Locale.SIMPLIFIED_CHINESE)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TodayScreen(viewModel: TodayViewModel) {
    val state by viewModel.uiState.collectAsState()
    val pomodoro by PomodoroTimer.state.collectAsState()
    val focusMinutes by FocusTimeStore.minutes.collectAsState()
    val context = LocalContext.current
    var pendingStart by rememberSaveable { mutableStateOf<String?>(null) }
    var showDatePicker by rememberSaveable { mutableStateOf(false) }
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) {
        pendingStart?.let { taskId ->
            state.tasks.firstOrNull { task -> task.id == taskId }?.let { task ->
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

    if (showDatePicker) {
        val pickerState = rememberDatePickerState(
            initialSelectedDateMillis = state.date
                .atStartOfDay(ZoneOffset.UTC)
                .toInstant()
                .toEpochMilli(),
        )
        DatePickerDialog(
            onDismissRequest = { showDatePicker = false },
            confirmButton = {
                TextButton(
                    onClick = {
                        pickerState.selectedDateMillis?.let { millis ->
                            viewModel.selectDate(
                                Instant.ofEpochMilli(millis)
                                    .atZone(ZoneOffset.UTC)
                                    .toLocalDate(),
                            )
                        }
                        showDatePicker = false
                    },
                ) {
                    Text("确定")
                }
            },
            dismissButton = {
                TextButton(onClick = { showDatePicker = false }) {
                    Text("取消")
                }
            },
        ) {
            DatePicker(state = pickerState)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                navigationIcon = {
                    IconButton(onClick = { viewModel.selectDate(state.date.minusDays(1)) }) {
                        Icon(Icons.Outlined.ChevronLeft, contentDescription = "前一天")
                    }
                },
                title = {
                    Row(
                        modifier = Modifier
                            .clickable { showDatePicker = true }
                            .padding(horizontal = 8.dp, vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Column {
                            Text(
                                text = if (state.date == LocalDate.now()) "今日计划" else "学习计划",
                                style = MaterialTheme.typography.titleLarge,
                            )
                            Text(
                                text = state.date.format(dayFormatter),
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        Icon(
                            imageVector = Icons.Outlined.CalendarMonth,
                            contentDescription = "选择日期",
                            modifier = Modifier.size(18.dp),
                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                actions = {
                    if (state.date != LocalDate.now()) {
                        IconButton(onClick = { viewModel.selectDate(LocalDate.now()) }) {
                            Icon(Icons.Outlined.Restore, contentDescription = "回到今天")
                        }
                    }
                    IconButton(onClick = { viewModel.selectDate(state.date.plusDays(1)) }) {
                        Icon(Icons.Outlined.ChevronRight, contentDescription = "后一天")
                    }
                },
            )
        },
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
            contentPadding = PaddingValues(horizontal = 18.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            if (state.loading && state.tasks.isNotEmpty()) {
                item {
                    LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                }
            }
            if (state.fromCache) {
                item {
                    AppNotice(
                        text = "当前显示本地缓存，联网后自动更新",
                        tone = NoticeTone.OFFLINE,
                    )
                }
            }
            if (state.pendingCheckIns > 0) {
                item {
                    AppNotice(
                        text = "${state.pendingCheckIns} 条打卡等待同步",
                        tone = NoticeTone.WARNING,
                    )
                }
            }
            state.notice?.let { notice ->
                item {
                    AppNotice(
                        text = notice,
                        tone = if ("成功" in notice || "已同步" in notice) {
                            NoticeTone.SUCCESS
                        } else {
                            NoticeTone.INFO
                        },
                    )
                }
            }
            if (state.loading && state.tasks.isEmpty()) {
                item {
                    AppLoading("正在整理今日计划")
                }
            }
            if (pomodoro.phase != PomodoroPhase.IDLE) {
                item {
                    PomodoroCard(
                        state = pomodoro,
                        onPause = { PomodoroService.pause(context) },
                        onResume = { PomodoroService.resume(context) },
                        onStop = { PomodoroService.stop(context) },
                        onOpenFocus = { PomodoroTimer.showFocus() },
                        onDismiss = {
                            PomodoroTimer.clear()
                            viewModel.refresh()
                        },
                    )
                }
            }
            if (!state.loading || state.tasks.isNotEmpty()) {
                item {
                    DayOverviewCard(
                        planned = state.plannedMinutes,
                        completed = state.completedMinutes,
                        remaining = state.remainingMinutes,
                    )
                }
            }
            if (!state.loading && state.tasks.isEmpty()) {
                item {
                    AppEmptyState(
                        title = "今天暂时没有任务",
                        body = "${state.date} 尚未安排学习内容",
                        icon = Icons.Outlined.EventAvailable,
                    )
                }
            }
            items(state.tasks, key = { it.id }) { task ->
                TaskCard(
                    task = task,
                    pomodoroEnabled = !pomodoro.active,
                    pomodoroTaskId = pomodoro.taskId,
                    focusMinutes = focusMinutes[task.id] ?: 0,
                    onCheckIn = { minutes -> viewModel.checkIn(task.id, minutes) },
                    onStartPomodoro = { startPomodoro(task) },
                )
            }
        }
    }
}

@Composable
private fun DayOverviewCard(planned: Int, completed: Int, remaining: Int) {
    val progress = if (planned <= 0) 0f else (completed.toFloat() / planned).coerceIn(0f, 1f)
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer,
        ),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text(
                        text = "今日进度",
                        style = MaterialTheme.typography.titleMedium,
                    )
                    Text(
                        text = "保持节奏，比追赶更重要",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.75f),
                    )
                }
                Text(
                    text = "${(progress * 100).toInt()}%",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                )
            }
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(8.dp),
                trackColor = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.15f),
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                OverviewMetric("完成", formatMinutes(completed))
                OverviewMetric("剩余", formatMinutes(remaining))
                OverviewMetric("计划", formatMinutes(planned))
            }
        }
    }
}

@Composable
private fun OverviewMetric(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = value,
            style = MaterialTheme.typography.titleMedium,
        )
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.72f),
        )
    }
}

private fun formatMinutes(minutes: Int): String =
    if (minutes >= 60) {
        val hours = minutes / 60
        val rest = minutes % 60
        if (rest == 0) "${hours}小时" else "${hours}时${rest}分"
    } else {
        "${minutes}分钟"
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
    onOpenFocus: () -> Unit,
    onDismiss: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        if (state.phase == PomodoroPhase.FINISHED) {
            Column(
                modifier = Modifier.padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                AppStatusChip("专注完成", NoticeTone.SUCCESS)
                Text("专注时间已计入任务", style = MaterialTheme.typography.titleLarge)
                Text(
                    text = state.notice ?: "本次专注 ${state.elapsedMinutes} 分钟",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Button(
                    onClick = onDismiss,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Icon(Icons.Outlined.Check, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("完成")
                }
            }
        } else {
            val progress = if (state.totalSeconds == 0) {
                0f
            } else {
                state.elapsedSeconds.toFloat() / state.totalSeconds
            }
            val minutes = state.remainingSeconds / 60
            val seconds = state.remainingSeconds % 60
            Row(
                modifier = Modifier.padding(18.dp),
                horizontalArrangement = Arrangement.spacedBy(18.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(
                        progress = { progress },
                        modifier = Modifier.size(92.dp),
                        strokeWidth = 7.dp,
                        trackColor = MaterialTheme.colorScheme.outlineVariant,
                    )
                    Text(
                        text = "%02d:%02d".format(minutes, seconds),
                        style = MaterialTheme.typography.titleLarge,
                    )
                }
                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    AppStatusChip(
                        label = if (state.phase == PomodoroPhase.PAUSED) "已暂停" else "专注中",
                        tone = if (state.phase == PomodoroPhase.PAUSED) {
                            NoticeTone.WARNING
                        } else {
                            NoticeTone.INFO
                        },
                    )
                    Text(
                        text = state.taskTitle,
                        style = MaterialTheme.typography.titleMedium,
                        maxLines = 2,
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilledTonalButton(
                            onClick = if (state.phase == PomodoroPhase.PAUSED) onResume else onPause,
                        ) {
                            Icon(
                                imageVector = if (state.phase == PomodoroPhase.PAUSED) {
                                    Icons.Outlined.PlayArrow
                                } else {
                                    Icons.Outlined.Pause
                                },
                                contentDescription = null,
                            )
                            Text(if (state.phase == PomodoroPhase.PAUSED) "继续" else "暂停")
                        }
                        IconButton(onClick = onStop) {
                            Icon(Icons.Outlined.Stop, contentDescription = "结束番茄钟")
                        }
                    }
                    TextButton(onClick = onOpenFocus) {
                        Text("进入专注页")
                    }
                }
            }
        }
    }
}

@Composable
private fun TaskCard(
    task: TodayTaskEntity,
    pomodoroEnabled: Boolean,
    pomodoroTaskId: String,
    focusMinutes: Int,
    onCheckIn: (Int) -> Unit,
    onStartPomodoro: () -> Unit,
) {
    var minutesInput by rememberSaveable(task.id) { mutableStateOf("") }
    var editingMinutes by rememberSaveable(task.id) { mutableStateOf(false) }
    val completed = task.status == "completed"

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (completed) {
                MaterialTheme.colorScheme.surface.copy(alpha = 0.72f)
            } else {
                MaterialTheme.colorScheme.surfaceVariant
            },
        ),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top,
            ) {
                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    Text(task.title, style = MaterialTheme.typography.titleMedium)
                    Text(
                        text = "${task.subjectName} / ${task.knowledgePointName}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Spacer(Modifier.width(12.dp))
                AppStatusChip(
                    label = when {
                        completed -> "已完成"
                        task.status == "skipped" -> "已跳过"
                        pomodoroTaskId == task.id -> "专注中"
                        else -> "待完成"
                    },
                    tone = when {
                        completed -> NoticeTone.SUCCESS
                        task.status == "skipped" -> NoticeTone.OFFLINE
                        pomodoroTaskId == task.id -> NoticeTone.INFO
                        task.carryCount > 0 -> NoticeTone.WARNING
                        else -> NoticeTone.OFFLINE
                    },
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                AppStatusChip("预计 ${formatMinutes(task.estMinutes)}", NoticeTone.OFFLINE)
                if (!completed && focusMinutes > 0) {
                    AppStatusChip("已计时 ${formatMinutes(focusMinutes)}", NoticeTone.INFO)
                }
                if (task.carryCount > 0) {
                    AppStatusChip("顺延 ${task.carryCount} 次", NoticeTone.WARNING)
                }
            }
            when {
                completed -> {
                    Text(
                        text = "实际完成 ${formatMinutes(task.actualMinutes ?: task.estMinutes)}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
                task.status == "skipped" -> {
                    Text(
                        text = "这项任务已跳过",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                editingMinutes -> {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        OutlinedTextField(
                            value = minutesInput,
                            onValueChange = { minutesInput = it.filter(Char::isDigit) },
                            label = { Text("实际耗时") },
                            suffix = { Text("分钟") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            modifier = Modifier.weight(1f),
                        )
                        Button(
                            onClick = {
                                minutesInput.toIntOrNull()?.let(onCheckIn)
                                editingMinutes = false
                            },
                            enabled = minutesInput.toIntOrNull()?.let { it in 0..1440 } == true,
                        ) {
                            Text("按此耗时打卡")
                        }
                    }
                    TextButton(onClick = { editingMinutes = false }) {
                        Text("取消")
                    }
                }
                else -> {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        Button(
                            onClick = onStartPomodoro,
                            enabled = pomodoroEnabled,
                            modifier = Modifier.weight(1f),
                        ) {
                            Icon(Icons.Outlined.PlayArrow, contentDescription = null)
                            Spacer(Modifier.width(6.dp))
                            Text("专注 ${pomodoroMinutes(task.estMinutes)} 分钟")
                        }
                        FilledTonalButton(
                            onClick = {
                                if (focusMinutes > 0) {
                                    onCheckIn(focusMinutes)
                                } else {
                                    minutesInput = ""
                                    editingMinutes = true
                                }
                            },
                        ) {
                            Icon(Icons.Outlined.Check, contentDescription = null)
                            Spacer(Modifier.width(4.dp))
                            Text(if (focusMinutes > 0) "完成 ${formatMinutes(focusMinutes)}" else "完成")
                        }
                    }
                    TextButton(
                        onClick = {
                            minutesInput = if (focusMinutes > 0) focusMinutes.toString() else ""
                            editingMinutes = true
                        },
                    ) {
                        Icon(
                            Icons.Outlined.Edit,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp),
                        )
                        Spacer(Modifier.width(6.dp))
                        Text("手动填耗时打卡")
                    }
                }
            }
        }
    }
}

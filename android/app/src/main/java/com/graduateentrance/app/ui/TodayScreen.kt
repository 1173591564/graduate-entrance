package com.graduateentrance.app.ui

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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.graduateentrance.app.data.local.TodayTaskEntity

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TodayScreen(viewModel: TodayViewModel) {
    val state by viewModel.uiState.collectAsState()

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
                TaskCard(task = task, onCheckIn = { minutes ->
                    viewModel.checkIn(task.id, minutes)
                })
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

@Composable
private fun TaskCard(task: TodayTaskEntity, onCheckIn: (Int) -> Unit) {
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
            }
        }
    }
}

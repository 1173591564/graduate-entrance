package com.graduateentrance.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Send
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.AutoStories
import androidx.compose.material.icons.outlined.ChatBubbleOutline
import androidx.compose.material.icons.outlined.Menu
import androidx.compose.material.icons.outlined.PhotoCamera
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Today
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    state: TodayUiState,
    onOpenDrawer: () -> Unit,
    onNavigate: (AppDestination) -> Unit,
) {
    var questionDraft by rememberSaveable { mutableStateOf("") }
    val nextTask = state.tasks.firstOrNull { it.status != "completed" && it.status != "skipped" }

    Scaffold(
        topBar = {
            TopAppBar(
                navigationIcon = {
                    IconButton(onClick = onOpenDrawer) {
                        Icon(Icons.Outlined.Menu, contentDescription = "打开导航抽屉")
                    }
                },
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("11408")
                        Spacer(Modifier.width(8.dp))
                        AppStatusChip("备考助手", NoticeTone.INFO)
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
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            item {
                GreetingCard(
                    planned = state.plannedMinutes,
                    completed = state.completedMinutes,
                    remainingTasks = state.tasks.count {
                        it.status != "completed" && it.status != "skipped"
                    },
                    nextTaskTitle = nextTask?.title,
                    onOpenToday = { onNavigate(AppDestination.TODAY) },
                )
            }
            item {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(homeActions, key = { it.label }) { action ->
                        FilterChip(
                            selected = false,
                            onClick = { onNavigate(action.destination) },
                            leadingIcon = {
                                Icon(
                                    imageVector = action.icon,
                                    contentDescription = null,
                                )
                            },
                            label = { Text(action.label) },
                        )
                    }
                }
            }
            item {
                QuickStatsCard(state = state)
            }
            item {
                ChatEntryCard(
                    value = questionDraft,
                    onValueChange = { questionDraft = it },
                    onCapture = { onNavigate(AppDestination.CAPTURE) },
                )
            }
        }
    }
}

private data class HomeAction(
    val label: String,
    val destination: AppDestination,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
)

private val homeActions = listOf(
    HomeAction("今日任务", AppDestination.TODAY, Icons.Outlined.Today),
    HomeAction("拍题", AppDestination.CAPTURE, Icons.Outlined.PhotoCamera),
    HomeAction("复习卡", AppDestination.REVIEWS, Icons.Outlined.AutoStories),
    HomeAction("设置", AppDestination.SETTINGS, Icons.Outlined.Settings),
)

@Composable
private fun GreetingCard(
    planned: Int,
    completed: Int,
    remainingTasks: Int,
    nextTaskTitle: String?,
    onOpenToday: () -> Unit,
) {
    val progress = if (planned <= 0) 0f else (completed.toFloat() / planned).coerceIn(0f, 1f)
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer,
        ),
    ) {
        Column(
            modifier = Modifier.padding(22.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(
                text = "今天先做最小可执行的一步",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = if (remainingTasks > 0) {
                    "还有 $remainingTasks 个任务 · 已完成 ${completed} / ${planned} 分钟"
                } else {
                    "今日计划已清空，保持复盘节奏"
                },
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.78f),
            )
            androidx.compose.material3.LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(8.dp),
            )
            androidx.compose.material3.Button(
                onClick = onOpenToday,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Outlined.Today, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text(nextTaskTitle ?: "查看今日计划")
            }
        }
    }
}

@Composable
private fun QuickStatsCard(state: TodayUiState) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("同步与节奏", style = MaterialTheme.typography.titleMedium)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                AppStatusChip(
                    label = if (state.fromCache) "离线缓存" else "在线同步",
                    tone = if (state.fromCache) NoticeTone.OFFLINE else NoticeTone.SUCCESS,
                )
                AppStatusChip(
                    label = if (state.pendingCheckIns > 0) {
                        "${state.pendingCheckIns} 条待传"
                    } else {
                        "无待同步"
                    },
                    tone = if (state.pendingCheckIns > 0) NoticeTone.WARNING else NoticeTone.SUCCESS,
                )
            }
        }
    }
}

@Composable
private fun ChatEntryCard(
    value: String,
    onValueChange: (String) -> Unit,
    onCapture: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("随手记录疑问", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                value = value,
                onValueChange = onValueChange,
                placeholder = { Text("这道题为什么这样转化？") },
                leadingIcon = {
                    IconButton(onClick = onCapture) {
                        Icon(Icons.Outlined.Add, contentDescription = "拍题")
                    }
                },
                trailingIcon = {
                    Icon(
                        imageVector = if (value.isBlank()) {
                            Icons.Outlined.ChatBubbleOutline
                        } else {
                            Icons.AutoMirrored.Outlined.Send
                        },
                        contentDescription = null,
                    )
                },
                modifier = Modifier.fillMaxWidth(),
                minLines = 2,
            )
            Text(
                text = "当前版本先作为本地草稿入口；拍题可直接进入上传流程。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

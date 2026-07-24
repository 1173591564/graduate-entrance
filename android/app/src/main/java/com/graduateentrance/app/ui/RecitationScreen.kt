package com.graduateentrance.app.ui

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AutoStories
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.graduateentrance.app.network.RecitationItemDto

private val subjectLabels = listOf(
    "politics" to "政治",
    "english" to "英语",
    "math" to "数学",
    "cs408" to "408",
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RecitationScreen(viewModel: RecitationViewModel) {
    val state by viewModel.uiState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(state.notice) {
        state.notice?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.consumeNotice()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("每日一背")
                        state.stats?.let {
                            Text(
                                text = "共 ${it.totalCount} 条 · 今日已背 ${it.recitedToday}",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                },
                actions = {
                    IconButton(onClick = viewModel::refresh) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "刷新")
                    }
                },
            )
        },
    ) { innerPadding ->
        when {
            state.loading && state.stats == null -> AppLoading(
                label = "正在加载背诵材料",
                modifier = Modifier.padding(innerPadding),
            )
            state.error != null -> Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
                    .padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                AppNotice(state.error!!, NoticeTone.ERROR)
                Button(onClick = viewModel::refresh, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Outlined.Refresh, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("重新加载")
                }
            }
            else -> PullToRefreshBox(
                isRefreshing = state.loading,
                onRefresh = viewModel::refresh,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 16.dp)
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(14.dp),
                ) {
                    RecitationContent(state = state, viewModel = viewModel)
                    Spacer(Modifier.width(1.dp))
                }
            }
        }
    }
}

@Composable
private fun RecitationContent(
    state: RecitationUiState,
    viewModel: RecitationViewModel,
) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        subjectLabels.forEach { (subject, label) ->
            FilterChip(
                selected = state.subject == subject,
                onClick = { viewModel.switchSubject(subject) },
                label = { Text(label) },
            )
        }
    }
    if ((state.stats?.totalCount ?: 0) == 0) {
        AppEmptyState(
            title = "背诵池是空的",
            body = "重启后端会自动导入种子材料，或在 Web 后台导入。",
            icon = Icons.Outlined.AutoStories,
        )
    } else {
        when {
            state.queue.isNotEmpty() -> QueueRecitationCard(
                state = state,
                viewModel = viewModel,
            )
            state.queueInitialSize > 0 -> QueueDoneCard(state = state)
            else -> state.today?.let { today ->
                TodayRecitationCard(
                    item = today,
                    busy = today.id in state.busy,
                    onRecite = { undo -> viewModel.recite(today.id, undo) },
                )
            }
        }
        state.groups.forEach { group ->
            Text(
                text = group.category,
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            group.items.forEach { item ->
                RecitationRow(
                    item = item,
                    busy = item.id in state.busy,
                    expanded = item.id in state.expanded,
                    onToggle = { viewModel.toggleExpanded(item.id) },
                    onRecite = { undo -> viewModel.recite(item.id, undo) },
                )
            }
        }
    }
}

@Composable
private fun QueueRecitationCard(
    state: RecitationUiState,
    viewModel: RecitationViewModel,
) {
    val item = state.queueCurrent ?: return
    val busy = item.id in state.busy
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("今日应背", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.width(10.dp))
                AppStatusChip(
                    label = "第 ${state.queueGradedCount + 1}/${state.queueInitialSize} 条",
                    tone = NoticeTone.WARNING,
                )
                if (item.reciteCount > 0) {
                    Spacer(Modifier.width(8.dp))
                    AppStatusChip(label = "到期复习", tone = NoticeTone.OFFLINE)
                }
            }
            Text(
                text = "${item.category} · 已背 ${item.reciteCount} 次",
                style = MaterialTheme.typography.labelMedium,
            )
            Text(
                text = item.title,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold,
            )
            if (!state.revealed) {
                Text(
                    text = "先尝试回忆内容，再展开对答案",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Button(
                    onClick = viewModel::reveal,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("想好了，对答案")
                }
            } else {
                MarkdownText(
                    markdown = item.contentMd,
                    style = MaterialTheme.typography.bodyLarge,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(
                        onClick = { viewModel.gradeCurrent("forgot") },
                        enabled = !busy,
                        modifier = Modifier.weight(1f),
                    ) {
                        Text("忘了")
                    }
                    OutlinedButton(
                        onClick = { viewModel.gradeCurrent("vague") },
                        enabled = !busy,
                        modifier = Modifier.weight(1f),
                    ) {
                        Text("模糊")
                    }
                    Button(
                        onClick = { viewModel.gradeCurrent("mastered") },
                        enabled = !busy,
                        modifier = Modifier.weight(1f),
                    ) {
                        Text("记得")
                    }
                }
            }
        }
    }
}

@Composable
private fun QueueDoneCard(state: RecitationUiState) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("今日应背完成", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.width(10.dp))
                AppStatusChip(label = "已背 ${state.queueGradedCount} 条", tone = NoticeTone.SUCCESS)
            }
            Text(
                text = if (state.taskCheckedIn) {
                    "已自动打卡今日背诵任务，明天到期的内容会自动出现"
                } else {
                    "到期复习和新内容会按记忆曲线自动安排到后续日期"
                },
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun TodayRecitationCard(
    item: RecitationItemDto,
    busy: Boolean,
    onRecite: (Boolean) -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("今日一背", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.width(10.dp))
                AppStatusChip(
                    label = if (item.recitedToday) "已打卡" else "待背诵",
                    tone = if (item.recitedToday) NoticeTone.SUCCESS else NoticeTone.WARNING,
                )
            }
            Text(
                text = "${item.category} · 已背 ${item.reciteCount} 次",
                style = MaterialTheme.typography.labelMedium,
            )
            Text(
                text = item.title,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold,
            )
            MarkdownText(
                markdown = item.contentMd,
                style = MaterialTheme.typography.bodyLarge,
            )
            ReciteButton(
                recitedToday = item.recitedToday,
                busy = busy,
                doneLabel = "撤销打卡",
                pendingLabel = "背完打卡",
                onRecite = onRecite,
            )
        }
    }
}

@Composable
private fun ReciteButton(
    recitedToday: Boolean,
    busy: Boolean,
    doneLabel: String,
    pendingLabel: String,
    onRecite: (Boolean) -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    if (recitedToday) {
        OutlinedButton(onClick = { onRecite(true) }, enabled = !busy) {
            Text(doneLabel)
        }
    } else {
        Button(
            onClick = {
                haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                onRecite(false)
            },
            enabled = !busy,
        ) {
            if (busy) {
                CircularProgressIndicator(
                    modifier = Modifier.size(16.dp),
                    strokeWidth = 2.dp,
                    color = MaterialTheme.colorScheme.onPrimary,
                )
                Spacer(Modifier.width(8.dp))
            }
            Text(pendingLabel)
        }
    }
}

@Composable
private fun RecitationRow(
    item: RecitationItemDto,
    busy: Boolean,
    expanded: Boolean,
    onToggle: () -> Unit,
    onRecite: (Boolean) -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .animateContentSize(),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(onClick = onToggle),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = item.title,
                    style = MaterialTheme.typography.bodyLarge,
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(10.dp))
                if (item.recitedToday) {
                    AppStatusChip(label = "今日已背", tone = NoticeTone.SUCCESS)
                } else {
                    AppStatusChip(label = "${item.reciteCount} 次", tone = NoticeTone.OFFLINE)
                }
            }
            if (expanded) {
                MarkdownText(
                    markdown = item.contentMd,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = onToggle) {
                    Text(if (expanded) "收起" else "展开")
                }
                ReciteButton(
                    recitedToday = item.recitedToday,
                    busy = busy,
                    doneLabel = "撤销",
                    pendingLabel = "打卡",
                    onRecite = onRecite,
                )
            }
        }
    }
}

package com.graduateentrance.app.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
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
import androidx.compose.material.icons.outlined.MenuBook
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
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
import com.graduateentrance.app.network.PaperDto

private val statusLabels = mapOf("unread" to "未读", "reading" to "在读", "done" to "已读")

private fun statusTone(status: String): NoticeTone = when (status) {
    "reading" -> NoticeTone.WARNING
    "done" -> NoticeTone.SUCCESS
    else -> NoticeTone.OFFLINE
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PapersScreen(viewModel: PapersViewModel) {
    val state by viewModel.uiState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(state.notice) {
        state.notice?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.consumeNotice()
        }
    }

    state.reader?.let { reader ->
        BackHandler(onBack = viewModel::closeReader)
        PaperReaderScreen(
            state = reader,
            onClose = viewModel::closeReader,
            onSaveProgress = viewModel::saveReadingProgress,
            onAddAnnotation = viewModel::addAnnotation,
            onUpdateAnnotation = viewModel::updateAnnotation,
            onDeleteAnnotation = viewModel::deleteAnnotation,
        )
        return
    }

    state.viewer?.let { viewer ->
        BackHandler(onBack = viewModel::closeViewer)
        PdfViewerScreen(
            file = viewer.file,
            title = viewer.title,
            onClose = viewModel::closeViewer,
        )
        return
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("英语阅读训练")
                        state.stats?.let {
                            Text(
                                text = "共 ${it.totalCount} 篇 · 已读 ${it.doneCount}",
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
                label = "正在加载阅读材料",
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
            (state.stats?.totalCount ?: 0) == 0 -> AppEmptyState(
                title = "阅读池是空的",
                body = "先在 Web 后台同步论文素材，再回来读。",
                icon = Icons.Outlined.MenuBook,
                modifier = Modifier.padding(innerPadding),
            )
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
                    state.today?.let { today ->
                        TodayPaperCard(
                            paper = today,
                            busy = today.id in state.busy,
                            onStatus = { viewModel.setStatus(today.id, it) },
                            onOpen = { viewModel.openPaper(today) },
                            onRead = { viewModel.openReader(today) },
                        )
                    }
                    state.groups.forEach { group ->
                        Text(
                            text = group.category,
                            style = MaterialTheme.typography.titleSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        group.papers.forEach { paper ->
                            PaperRow(
                                paper = paper,
                                busy = paper.id in state.busy,
                                onStatus = { viewModel.setStatus(paper.id, it) },
                                onOpen = { viewModel.openPaper(paper) },
                                onRead = { viewModel.openReader(paper) },
                            )
                        }
                    }
                    Spacer(Modifier.width(1.dp))
                }
            }
        }
    }
}

@Composable
private fun TodayPaperCard(
    paper: PaperDto,
    busy: Boolean,
    onStatus: (String) -> Unit,
    onOpen: () -> Unit,
    onRead: () -> Unit,
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
                Text("今日一篇", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.width(10.dp))
                AppStatusChip(
                    label = statusLabels[paper.status] ?: paper.status,
                    tone = statusTone(paper.status),
                )
            }
            Text(paper.category, style = MaterialTheme.typography.labelMedium)
            Text(
                text = paper.title,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold,
            )
            PaperActions(
                paper = paper,
                busy = busy,
                onStatus = onStatus,
                onOpen = onOpen,
                onRead = onRead,
            )
        }
    }
}

@Composable
private fun PaperRow(
    paper: PaperDto,
    busy: Boolean,
    onStatus: (String) -> Unit,
    onOpen: () -> Unit,
    onRead: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = paper.title,
                    style = MaterialTheme.typography.bodyLarge,
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(10.dp))
                AppStatusChip(
                    label = statusLabels[paper.status] ?: paper.status,
                    tone = statusTone(paper.status),
                )
            }
            PaperActions(
                paper = paper,
                busy = busy,
                onStatus = onStatus,
                onOpen = onOpen,
                onRead = onRead,
            )
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun PaperActions(
    paper: PaperDto,
    busy: Boolean,
    onStatus: (String) -> Unit,
    onOpen: () -> Unit,
    onRead: () -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        if (paper.status != "reading") {
            OutlinedButton(
                onClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onStatus("reading")
                },
                enabled = !busy,
            ) {
                Text("在读")
            }
        }
        if (paper.status != "done") {
            Button(
                onClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onStatus("done")
                },
                enabled = !busy,
            ) {
                Text("已读")
            }
        }
        if (paper.status != "unread") {
            TextButton(onClick = { onStatus("unread") }, enabled = !busy) {
                Text("重置")
            }
        }
        if (paper.hasContent == true) {
            Button(onClick = onRead, enabled = !busy) {
                Text("阅读")
            }
        }
        if (paper.hasFile) {
            TextButton(onClick = onOpen, enabled = !busy) {
                if (busy) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        strokeWidth = 2.dp,
                    )
                    Spacer(Modifier.width(8.dp))
                    Text("正在打开…")
                } else {
                    Text("打开 PDF")
                }
            }
        }
    }
}

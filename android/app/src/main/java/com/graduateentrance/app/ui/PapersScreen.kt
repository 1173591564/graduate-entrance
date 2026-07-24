package com.graduateentrance.app.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.MenuBook
import androidx.compose.material.icons.outlined.PictureAsPdf
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.graduateentrance.app.data.PaperItem
import com.graduateentrance.app.data.PaperStats

private val statusLabels = mapOf("unread" to "未读", "reading" to "在读", "done" to "已读")

private fun statusTone(status: String): NoticeTone = when (status) {
    "reading" -> NoticeTone.WARNING
    "done" -> NoticeTone.SUCCESS
    else -> NoticeTone.OFFLINE
}

@Composable
private fun spineColor(status: String): Color = when (status) {
    "reading" -> MaterialTheme.colorScheme.tertiary
    "done" -> MaterialTheme.colorScheme.primary
    else -> MaterialTheme.colorScheme.outlineVariant
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
            onMarkDone = { viewModel.setStatus(reader.paper.id, "done") },
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
                title = { Text("书架") },
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
                label = "正在整理书架",
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
                title = "书架是空的",
                body = "先在 Web 后台同步论文素材，再回来读。",
                icon = Icons.AutoMirrored.Outlined.MenuBook,
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
                    Spacer(Modifier.height(2.dp))
                    state.stats?.let { ShelfProgressCard(it) }
                    state.groups.forEach { group ->
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                text = group.category,
                                style = MaterialTheme.typography.titleSmall,
                                color = MaterialTheme.colorScheme.onSurface,
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(
                                text = "${group.papers.size}",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
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
                    }
                    Spacer(Modifier.height(8.dp))
                }
            }
        }
    }
}

@Composable
private fun ShelfProgressCard(stats: PaperStats) {
    val ratio = if (stats.totalCount > 0) {
        stats.doneCount.toFloat() / stats.totalCount
    } else {
        0f
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer,
        ),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Bottom,
            ) {
                Column {
                    Text(
                        text = "阅读进度",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f),
                    )
                    Text(
                        text = "已读 ${stats.doneCount} / ${stats.totalCount}",
                        style = MaterialTheme.typography.headlineSmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                    )
                }
                Text(
                    text = "${(ratio * 100).toInt()}%",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                )
            }
            LinearProgressIndicator(
                progress = { ratio },
                modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)),
                color = MaterialTheme.colorScheme.primary,
                trackColor = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.15f),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                StatPill("在读", stats.readingCount)
                StatPill("未读", stats.unreadCount)
            }
        }
    }
}

@Composable
private fun StatPill(label: String, value: Int) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            text = "$value",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onPrimaryContainer,
        )
        Spacer(Modifier.width(4.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f),
        )
    }
}

@Composable
private fun PaperRow(
    paper: PaperItem,
    busy: Boolean,
    onStatus: (String) -> Unit,
    onOpen: () -> Unit,
    onRead: () -> Unit,
) {
    val clickable = paper.hasContent || paper.hasFile
    Card(
        modifier = Modifier.fillMaxWidth().let {
            if (clickable) {
                it.clickable(enabled = !busy) {
                    if (paper.hasContent) onRead() else onOpen()
                }
            } else {
                it
            }
        },
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height(64.dp)
                    .background(spineColor(paper.status)),
            )
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 14.dp, top = 12.dp, bottom = 12.dp, end = 8.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Text(
                    text = paper.title,
                    style = MaterialTheme.typography.bodyLarge.copy(fontFamily = FontFamily.Serif),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = statusLabels[paper.status] ?: paper.status,
                        style = MaterialTheme.typography.labelSmall,
                        color = when (statusTone(paper.status)) {
                            NoticeTone.SUCCESS -> MaterialTheme.colorScheme.primary
                            NoticeTone.WARNING -> MaterialTheme.colorScheme.tertiary
                            else -> MaterialTheme.colorScheme.onSurfaceVariant
                        },
                    )
                    if (paper.hasContent) {
                        Text(
                            text = " · 可精读",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
            if (busy) {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp).padding(end = 4.dp),
                    strokeWidth = 2.dp,
                )
            }
            if (paper.hasFile) {
                PdfIconButton(busy = busy, onClick = onOpen)
            }
            StatusMenuButton(paper = paper, busy = busy, onStatus = onStatus)
            Spacer(Modifier.width(4.dp))
        }
    }
}

@Composable
private fun PdfIconButton(busy: Boolean, onClick: () -> Unit) {
    IconButton(onClick = onClick, enabled = !busy) {
        Icon(
            Icons.Outlined.PictureAsPdf,
            contentDescription = "打开 PDF",
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun StatusMenuButton(
    paper: PaperItem,
    busy: Boolean,
    onStatus: (String) -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    var expanded by remember { mutableStateOf(false) }
    Box {
        Surface(
            shape = MaterialTheme.shapes.extraLarge,
            color = MaterialTheme.colorScheme.surfaceVariant,
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
            modifier = Modifier.clickable(enabled = !busy) { expanded = true },
        ) {
            Text(
                text = "标记",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
            )
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            listOf("unread", "reading", "done").forEach { status ->
                DropdownMenuItem(
                    text = {
                        Text(
                            text = statusLabels[status] ?: status,
                            fontWeight = if (paper.status == status) {
                                FontWeight.Bold
                            } else {
                                FontWeight.Normal
                            },
                        )
                    },
                    onClick = {
                        expanded = false
                        if (paper.status != status) {
                            haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                            onStatus(status)
                        }
                    },
                )
            }
        }
    }
}

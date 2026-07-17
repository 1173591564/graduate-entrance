package com.graduateentrance.app.ui

import androidx.compose.animation.Crossfade
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Translate
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.graduateentrance.app.network.VocabWordDto

private data class GradeSpec(
    val grade: String,
    val label: String,
    val container: Color,
    val content: Color,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VocabScreen(viewModel: VocabViewModel) {
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
                        Text("背单词")
                        Text(
                            text = "已学 ${state.learnedCount} / ${state.totalCount}" +
                                " · 到期 ${state.dueCount}",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
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
            state.loading && state.queue.isEmpty() && state.totalCount == 0 -> AppLoading(
                label = "正在加载词库",
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
                    VocabSessionHeader(state)
                    val current = state.current
                    if (current == null) {
                        AppEmptyState(
                            title = if (state.totalCount == 0) "词库是空的" else "今日单词已背完",
                            body = if (state.totalCount == 0) {
                                "在 Web 后台导入红宝书词表后即可开始。"
                            } else {
                                "到期与新词都清空了，明天再来吧。"
                            },
                            icon = Icons.Outlined.CheckCircle,
                        )
                    } else {
                        VocabCard(
                            word = current,
                            revealed = state.revealed,
                            grading = state.grading,
                            onReveal = viewModel::reveal,
                            onGrade = { grade -> viewModel.grade(current.id, grade) },
                        )
                    }
                    Spacer(Modifier.width(1.dp))
                }
            }
        }
    }
}

@Composable
private fun VocabSessionHeader(state: VocabUiState) {
    val total = state.sessionTotal
    val progress = if (total <= 0) 0f else (state.gradedCount.toFloat() / total).coerceIn(0f, 1f)
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = if (total == 0) "今日无待背单词" else "本轮进度 ${state.gradedCount} / $total",
                style = MaterialTheme.typography.titleMedium,
            )
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun VocabCard(
    word: VocabWordDto,
    revealed: Boolean,
    grading: Boolean,
    onReveal: () -> Unit,
    onGrade: (String) -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                AppStatusChip(
                    label = if (word.dueDate == null) "新词" else "复习",
                    tone = if (word.dueDate == null) NoticeTone.INFO else NoticeTone.WARNING,
                )
                if (word.reps > 0) {
                    AppStatusChip(label = "已背 ${word.reps} 次", tone = NoticeTone.OFFLINE)
                }
                AppStatusChip(label = "P${word.bookPage}", tone = NoticeTone.OFFLINE)
            }
            Text(
                text = word.word,
                style = MaterialTheme.typography.displaySmall,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
            )
            Crossfade(targetState = revealed, label = "meaning") { show ->
                if (show) {
                    Text(
                        text = word.meaning,
                        style = MaterialTheme.typography.titleMedium,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth(),
                    )
                } else {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable(onClick = onReveal),
                        contentAlignment = Alignment.Center,
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(6.dp),
                        ) {
                            Icon(
                                Icons.Outlined.Translate,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            Text(
                                text = "点击查看释义",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }
            if (revealed) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    gradeSpecs.forEach { spec ->
                        Button(
                            onClick = {
                                haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                                onGrade(spec.grade)
                            },
                            enabled = !grading,
                            modifier = Modifier.weight(1f),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = spec.container,
                                contentColor = spec.content,
                            ),
                        ) {
                            if (grading) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(16.dp),
                                    strokeWidth = 2.dp,
                                    color = spec.content,
                                )
                            } else {
                                Text(spec.label)
                            }
                        }
                    }
                }
            } else {
                Button(onClick = onReveal, modifier = Modifier.fillMaxWidth()) {
                    Text("显示释义")
                }
            }
        }
    }
}

private val gradeSpecs = listOf(
    GradeSpec("forgot", "忘了", Color(0xFF5A1A1A), Color(0xFFFFDAD6)),
    GradeSpec("vague", "模糊", Color(0xFF4A3513), Color(0xFFFFDDB0)),
    GradeSpec("mastered", "掌握", Color(0xFF173F2B), Color(0xFFC4EED3)),
)

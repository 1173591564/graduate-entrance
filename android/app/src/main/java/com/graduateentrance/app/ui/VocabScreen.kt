package com.graduateentrance.app.ui

import android.media.AudioAttributes
import android.media.MediaPlayer
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
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.VolumeUp
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.EditNote
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
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
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
import java.net.URLEncoder

private data class GradeSpec(
    val grade: String,
    val label: String,
    val container: Color,
    val content: Color,
)

private fun playPronunciation(word: String) {
    val encoded = URLEncoder.encode(word, "UTF-8")
    val player = MediaPlayer()
    player.setAudioAttributes(
        AudioAttributes.Builder()
            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
            .setUsage(AudioAttributes.USAGE_MEDIA)
            .build(),
    )
    try {
        player.setDataSource("https://dict.youdao.com/dictvoice?audio=$encoded&type=2")
        player.setOnPreparedListener { it.start() }
        player.setOnCompletionListener { it.release() }
        player.setOnErrorListener { mp, _, _ ->
            mp.release()
            true
        }
        player.prepareAsync()
    } catch (_: Exception) {
        player.release()
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VocabScreen(viewModel: VocabViewModel) {
    val state by viewModel.uiState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    if (state.dictationActive) {
        DictationScreen(state = state, viewModel = viewModel)
        return
    }

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
                    IconButton(onClick = viewModel::startDictation) {
                        Icon(Icons.Outlined.EditNote, contentDescription = "今日默写")
                    }
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
                    if (state.gradedCount > 0 || state.dictationTotalToday > 0) {
                        DictationPromptCard(
                            state = state,
                            onStart = viewModel::startDictation,
                        )
                    }
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
                            enriching = state.enriching,
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
private fun DictationPromptCard(state: VocabUiState, onStart: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.secondaryContainer,
        ),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Icon(
                Icons.Outlined.EditNote,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSecondaryContainer,
            )
            Text(
                text = if (state.dictationTotalToday > 0) {
                    "今日已默写 ${state.dictationCorrectToday} / ${state.dictationTotalToday} 对"
                } else {
                    "今天已背 ${state.gradedCount} 个词，默写一遍更牢固"
                },
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSecondaryContainer,
                modifier = Modifier.weight(1f),
            )
            Button(onClick = onStart) {
                Text(if (state.dictationTotalToday > 0) "再默一轮" else "去默写")
            }
        }
    }
}

@Composable
private fun VocabCard(
    word: VocabWordDto,
    revealed: Boolean,
    grading: Boolean,
    enriching: Boolean,
    onReveal: () -> Unit,
    onGrade: (String) -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    val revealAndPlay = {
        onReveal()
        playPronunciation(word.word)
    }
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
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Text(
                    text = word.word,
                    style = MaterialTheme.typography.displaySmall,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center,
                )
                IconButton(onClick = { playPronunciation(word.word) }) {
                    Icon(
                        Icons.AutoMirrored.Outlined.VolumeUp,
                        contentDescription = "播放读音",
                        tint = MaterialTheme.colorScheme.primary,
                    )
                }
            }
            if (word.phonetic.isNotBlank()) {
                Text(
                    text = word.phonetic,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Crossfade(targetState = revealed, label = "meaning") { show ->
                if (show) {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Text(
                            text = word.meaning,
                            style = MaterialTheme.typography.titleMedium,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth(),
                        )
                        when {
                            word.exampleEn.isNotBlank() -> Column(
                                modifier = Modifier.fillMaxWidth(),
                                verticalArrangement = Arrangement.spacedBy(4.dp),
                            ) {
                                Text(
                                    text = word.exampleEn,
                                    style = MaterialTheme.typography.bodyMedium,
                                )
                                if (word.exampleZh.isNotBlank()) {
                                    Text(
                                        text = word.exampleZh,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                            }
                            enriching -> Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(14.dp),
                                    strokeWidth = 2.dp,
                                )
                                Text(
                                    text = "正在生成音标与例句…",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                    }
                } else {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable(onClick = revealAndPlay),
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
                Button(onClick = revealAndPlay, modifier = Modifier.fillMaxWidth()) {
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DictationScreen(state: VocabUiState, viewModel: VocabViewModel) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(if (state.dictationRound > 1) "错词重默 · 第 ${state.dictationRound} 轮" else "今日默写")
                        Text(
                            text = if (state.dictationWords.isEmpty()) {
                                "根据释义写出单词"
                            } else {
                                "第 ${
                                    (state.dictationIndex + 1)
                                        .coerceAtMost(state.dictationWords.size)
                                } / ${state.dictationWords.size} 个 · 对 ${state.dictationCorrectCount}"
                            },
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = viewModel::exitDictation) {
                        Icon(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = "返回")
                    }
                },
            )
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            when {
                state.dictationLoading -> AppLoading(label = "正在加载今日已背单词")
                state.dictationWords.isEmpty() -> AppEmptyState(
                    title = "今天还没背单词",
                    body = "先去背几个单词，再来默写巩固。",
                    icon = Icons.Outlined.EditNote,
                )
                state.dictationDone -> Column(
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    AppEmptyState(
                        title = "默写完成",
                        body = buildString {
                            append(
                                "共 ${state.dictationFirstTotal} 个，首轮写对 " +
                                    "${state.dictationCorrectCount} 个。",
                            )
                            if (state.dictationRound > 1) {
                                append("\n错词已全部重默过关，明天还会再考。")
                            }
                            if (state.dictationTaskCheckedIn) {
                                append("\n已自动打卡今日默写任务。")
                            }
                        },
                        icon = Icons.Outlined.CheckCircle,
                    )
                    Button(
                        onClick = viewModel::exitDictation,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text("返回背单词")
                    }
                }
                else -> state.dictationCurrent?.let { word ->
                    DictationCard(state = state, word = word, viewModel = viewModel)
                }
            }
            Spacer(Modifier.width(1.dp))
        }
    }
}

@Composable
private fun DictationCard(
    state: VocabUiState,
    word: VocabWordDto,
    viewModel: VocabViewModel,
) {
    val correct = state.dictationLastCorrect
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
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text(
                    text = "释义",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                IconButton(onClick = { playPronunciation(word.word) }) {
                    Icon(
                        Icons.AutoMirrored.Outlined.VolumeUp,
                        contentDescription = "播放读音",
                        tint = MaterialTheme.colorScheme.primary,
                    )
                }
            }
            Text(
                text = word.meaning,
                style = MaterialTheme.typography.titleMedium,
            )
            OutlinedTextField(
                value = state.dictationInput,
                onValueChange = viewModel::setDictationInput,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("写出对应的单词") },
                singleLine = true,
                enabled = !state.dictationChecked,
            )
            if (state.dictationChecked) {
                AppNotice(
                    if (correct) "写对了！" else "不对，正确答案：${word.word}",
                    if (correct) NoticeTone.SUCCESS else NoticeTone.ERROR,
                )
                Button(
                    onClick = viewModel::nextDictation,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(
                        if (state.dictationIndex + 1 >= state.dictationWords.size) {
                            "查看结果"
                        } else {
                            "下一个"
                        },
                    )
                }
            } else {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    OutlinedButton(
                        onClick = viewModel::giveUpDictation,
                        modifier = Modifier.weight(1f),
                    ) {
                        Text("不会")
                    }
                    Button(
                        onClick = viewModel::checkDictation,
                        enabled = state.dictationInput.isNotBlank(),
                        modifier = Modifier.weight(2f),
                    ) {
                        Text("检查")
                    }
                }
            }
        }
    }
}

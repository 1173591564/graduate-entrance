package com.graduateentrance.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AutoStories
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Visibility
import androidx.compose.material.icons.outlined.VisibilityOff
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.graduateentrance.app.network.ReviewProblemDto

private val kindLabels = mapOf("wrong" to "错题", "hard" to "难题", "good" to "好题")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReviewsScreen(viewModel: ReviewsViewModel) {
    val state by viewModel.uiState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    var selectedSubject by rememberSaveable { mutableStateOf<String?>(null) }
    val subjects = state.problems.mapNotNull { it.subjectName }.distinct()
    val visibleProblems = state.problems.filter {
        selectedSubject == null || it.subjectName == selectedSubject
    }
    val currentProblem = visibleProblems.firstOrNull()

    LaunchedEffect(subjects, selectedSubject) {
        if (selectedSubject != null && selectedSubject !in subjects) {
            selectedSubject = null
        }
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
                        Text("专注复习")
                        if (state.asOf.isNotEmpty()) {
                            Text(
                                text = "${state.asOf} · 剩余 ${state.total} 题",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                },
                actions = {
                    IconButton(onClick = viewModel::refresh) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "刷新复习卡")
                    }
                },
            )
        },
    ) { innerPadding ->
        when {
            state.loading && state.problems.isEmpty() -> {
                AppLoading(
                    label = "正在准备复习卡",
                    modifier = Modifier.padding(innerPadding),
                )
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
                        .padding(horizontal = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    ReviewSessionHeader(
                        reviewed = state.reviewedCount,
                        total = state.sessionTotal,
                        includeDrafts = state.includeDrafts,
                        onIncludeDraftsChange = viewModel::setIncludeDrafts,
                    )
                    if (subjects.isNotEmpty()) {
                        LazyRow(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            contentPadding = PaddingValues(vertical = 2.dp),
                        ) {
                            item {
                                FilterChip(
                                    selected = selectedSubject == null,
                                    onClick = { selectedSubject = null },
                                    label = { Text("全部") },
                                )
                            }
                            items(subjects, key = { it }) { subject ->
                                FilterChip(
                                    selected = selectedSubject == subject,
                                    onClick = { selectedSubject = subject },
                                    label = { Text(subject) },
                                )
                            }
                        }
                    }
                    state.error?.let { error ->
                        AppNotice(error, NoticeTone.ERROR)
                        Button(
                            onClick = viewModel::refresh,
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Icon(Icons.Outlined.Refresh, contentDescription = null)
                            Spacer(Modifier.width(8.dp))
                            Text("重新加载")
                        }
                    }
                    if (state.error == null) {
                        if (currentProblem == null) {
                            AppEmptyState(
                                title = if (selectedSubject == null) {
                                    "本轮复习完成"
                                } else {
                                    "这个科目已清空"
                                },
                                body = if (selectedSubject == null) {
                                    "今天的到期题目已经处理完毕"
                                } else {
                                    "切换到全部题目继续复习"
                                },
                                icon = Icons.Outlined.CheckCircle,
                                actionLabel = if (selectedSubject == null) null else "查看全部",
                                onAction = if (selectedSubject == null) {
                                    null
                                } else {
                                    { selectedSubject = null }
                                },
                                modifier = Modifier.weight(1f),
                            )
                        } else {
                            ReviewCard(
                                problem = currentProblem,
                                grading = currentProblem.id in state.grading,
                                reviewed = state.reviewedCount,
                                total = state.sessionTotal,
                                onGrade = { grade -> viewModel.grade(currentProblem.id, grade) },
                                modifier = Modifier
                                    .weight(1f)
                                    .padding(bottom = 16.dp),
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ReviewSessionHeader(
    reviewed: Int,
    total: Int,
    includeDrafts: Boolean,
    onIncludeDraftsChange: (Boolean) -> Unit,
) {
    val progress = if (total <= 0) 0f else (reviewed.toFloat() / total).coerceIn(0f, 1f)
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
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = if (total == 0) "等待开始" else "本轮进度 $reviewed / $total",
                    style = MaterialTheme.typography.titleMedium,
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = "草稿",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Switch(
                        checked = includeDrafts,
                        onCheckedChange = onIncludeDraftsChange,
                        modifier = Modifier.size(width = 52.dp, height = 32.dp),
                    )
                }
            }
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun ReviewCard(
    problem: ReviewProblemDto,
    grading: Boolean,
    reviewed: Int,
    total: Int,
    onGrade: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var showSolutions by rememberSaveable(problem.id) { mutableStateOf(false) }

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 18.dp, vertical = 16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    AppStatusChip(
                        label = kindLabels[problem.kind] ?: problem.kind,
                        tone = when (problem.kind) {
                            "wrong" -> NoticeTone.ERROR
                            "hard" -> NoticeTone.WARNING
                            else -> NoticeTone.SUCCESS
                        },
                    )
                    AppStatusChip(
                        label = problem.subjectName ?: "未指定科目",
                        tone = NoticeTone.OFFLINE,
                    )
                }
                if (problem.status == "draft") {
                    AppStatusChip("草稿", NoticeTone.WARNING)
                }
            }
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
                contentPadding = PaddingValues(18.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                item {
                    Text(
                        text = problem.contentMd,
                        style = MaterialTheme.typography.bodyLarge,
                    )
                }
                if (problem.knowledgePoints.isNotEmpty()) {
                    item {
                        Text(
                            text = problem.knowledgePoints.joinToString(" · ") {
                                it.knowledgePointName
                            },
                            style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.primary,
                        )
                    }
                }
                if (problem.dueDate != null || problem.reps > 0) {
                    item {
                        Text(
                            text = buildList {
                                problem.dueDate?.let { add("到期 $it") }
                                if (problem.reps > 0) add("已复习 ${problem.reps} 次")
                            }.joinToString(" · "),
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                if (showSolutions) {
                    if (problem.solutions.isEmpty()) {
                        item {
                            AppNotice("这道题暂时没有已保存的解法", NoticeTone.WARNING)
                        }
                    } else {
                        items(problem.solutions, key = { it.id }) { solution ->
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                colors = CardDefaults.cardColors(
                                    containerColor = MaterialTheme.colorScheme.surface,
                                ),
                            ) {
                                Column(
                                    modifier = Modifier.padding(16.dp),
                                    verticalArrangement = Arrangement.spacedBy(8.dp),
                                ) {
                                    if (solution.methodTag.isNotEmpty() || !solution.verified) {
                                        Text(
                                            text = buildList {
                                                if (solution.methodTag.isNotEmpty()) {
                                                    add(solution.methodTag)
                                                }
                                                if (!solution.verified) {
                                                    add("待核验")
                                                }
                                            }.joinToString(" · "),
                                            style = MaterialTheme.typography.labelMedium,
                                            color = MaterialTheme.colorScheme.tertiary,
                                        )
                                    }
                                    Text(
                                        text = solution.contentMd,
                                        style = MaterialTheme.typography.bodyMedium,
                                    )
                                }
                            }
                        }
                    }
                }
            }
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
            Column(
                modifier = Modifier.padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                TextButton(
                    onClick = { showSolutions = !showSolutions },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Icon(
                        imageVector = if (showSolutions) {
                            Icons.Outlined.VisibilityOff
                        } else {
                            Icons.Outlined.Visibility
                        },
                        contentDescription = null,
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(if (showSolutions) "收起解法" else "翻面查看解法")
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    GradeButton(
                        label = "忘了",
                        grade = "forgot",
                        grading = grading,
                        onGrade = onGrade,
                        modifier = Modifier.weight(1f),
                        containerColor = MaterialTheme.colorScheme.errorContainer,
                        contentColor = MaterialTheme.colorScheme.onErrorContainer,
                    )
                    GradeButton(
                        label = "模糊",
                        grade = "vague",
                        grading = grading,
                        onGrade = onGrade,
                        modifier = Modifier.weight(1f),
                        containerColor = Color(0xFF4A3513),
                        contentColor = Color(0xFFFFDDB0),
                    )
                    GradeButton(
                        label = "掌握",
                        grade = "mastered",
                        grading = grading,
                        onGrade = onGrade,
                        modifier = Modifier.weight(1f),
                        containerColor = Color(0xFF173F2B),
                        contentColor = Color(0xFFC4EED3),
                    )
                }
                if (total > 0) {
                    Text(
                        text = "完成后自动进入下一题 · ${reviewed.coerceAtMost(total)} / $total",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.align(Alignment.CenterHorizontally),
                    )
                }
            }
        }
    }
}

@Composable
private fun GradeButton(
    label: String,
    grade: String,
    grading: Boolean,
    onGrade: (String) -> Unit,
    modifier: Modifier,
    containerColor: Color,
    contentColor: Color,
) {
    Button(
        onClick = { onGrade(grade) },
        enabled = !grading,
        modifier = modifier,
        colors = ButtonDefaults.buttonColors(
            containerColor = containerColor,
            contentColor = contentColor,
        ),
    ) {
        Text(label)
    }
}

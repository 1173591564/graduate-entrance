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
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
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
import com.graduateentrance.app.network.ReviewProblemDto

private val KIND_LABELS = mapOf("wrong" to "错题", "hard" to "难题", "good" to "好题")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReviewsScreen(viewModel: ReviewsViewModel) {
    val state by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("到期复习")
                        if (state.asOf.isNotEmpty()) {
                            Text(
                                text = "${state.asOf} · 共 ${state.total} 题",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                },
                actions = {
                    TextButton(onClick = { viewModel.refresh() }) {
                        Text("刷新")
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
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("包含草稿", style = MaterialTheme.typography.bodyLarge)
                    Switch(
                        checked = state.includeDrafts,
                        onCheckedChange = { viewModel.setIncludeDrafts(it) },
                    )
                }
            }
            state.notice?.let { notice ->
                item { ReviewNoticeCard(notice) }
            }
            state.error?.let { error ->
                item { ReviewNoticeCard(error) }
            }
            if (!state.loading && state.problems.isEmpty() && state.error == null) {
                item {
                    Text(
                        text = "今天没有到期的复习，继续保持！",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            items(state.problems, key = { it.id }) { problem ->
                ReviewCard(
                    problem = problem,
                    grading = problem.id in state.grading,
                    onGrade = { grade -> viewModel.grade(problem.id, grade) },
                )
            }
        }
    }
}

@Composable
private fun ReviewNoticeCard(text: String) {
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
private fun ReviewCard(
    problem: ReviewProblemDto,
    grading: Boolean,
    onGrade: (String) -> Unit,
) {
    var showSolutions by rememberSaveable(problem.id) { mutableStateOf(false) }

    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "${KIND_LABELS[problem.kind] ?: problem.kind} · " +
                        (problem.subjectName ?: "未指定科目"),
                    style = MaterialTheme.typography.titleMedium,
                )
                if (problem.status == "draft") {
                    Text(
                        text = "草稿",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.tertiary,
                    )
                }
            }
            Text(problem.contentMd, style = MaterialTheme.typography.bodyLarge)
            if (problem.knowledgePoints.isNotEmpty()) {
                Text(
                    text = problem.knowledgePoints.joinToString(" · ") { it.knowledgePointName },
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (problem.solutions.isNotEmpty()) {
                TextButton(onClick = { showSolutions = !showSolutions }) {
                    Text(if (showSolutions) "收起解法" else "查看解法（${problem.solutions.size}）")
                }
                if (showSolutions) {
                    problem.solutions.forEach { solution ->
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceContainerLow,
                            ),
                        ) {
                            Column(
                                modifier = Modifier.padding(12.dp),
                                verticalArrangement = Arrangement.spacedBy(6.dp),
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
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                                Text(
                                    solution.contentMd,
                                    style = MaterialTheme.typography.bodyMedium,
                                )
                            }
                        }
                    }
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                GradeButton("忘了", "forgot", grading, onGrade, Modifier.weight(1f), true)
                GradeButton("模糊", "vague", grading, onGrade, Modifier.weight(1f), false)
                GradeButton("掌握", "mastered", grading, onGrade, Modifier.weight(1f), false)
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
    modifier: Modifier = Modifier,
    isForgot: Boolean = false,
) {
    Button(
        onClick = { onGrade(grade) },
        enabled = !grading,
        modifier = modifier,
        colors = if (isForgot) {
            ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.errorContainer,
                contentColor = MaterialTheme.colorScheme.onErrorContainer,
            )
        } else {
            ButtonDefaults.buttonColors()
        },
    ) {
        Text(label)
    }
}

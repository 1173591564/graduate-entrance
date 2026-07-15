package com.graduateentrance.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.graduateentrance.app.network.ApiClient

private data class PlannedModule(
    val title: String,
    val summary: String,
)

private val plannedModules = listOf(
    PlannedModule("今日任务", "排程、计时、打卡与顺延"),
    PlannedModule("题库复习", "错题、知识点与 SM-2 复习"),
    PlannedModule("学习分析", "进度、掌握度与周报"),
    PlannedModule("离线同步", "本地事件队列与服务端合并"),
)

private enum class BackendStatus(val label: String) {
    Checking("后端连接中"),
    Online("后端已连接"),
    Offline("后端未连接"),
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GraduateEntranceApp() {
    var backendStatus by remember { mutableStateOf(BackendStatus.Checking) }

    LaunchedEffect(Unit) {
        backendStatus = runCatching { ApiClient.service.ping() }
            .fold(
                onSuccess = { BackendStatus.Online },
                onFailure = { BackendStatus.Offline },
            )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("11408 备考")
                        Text(
                            text = backendStatus.label,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
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
                Text(
                    text = "让每天的备考任务清晰、可执行、可复盘。",
                    style = MaterialTheme.typography.headlineMedium,
                    modifier = Modifier.padding(bottom = 12.dp),
                )
            }
            items(plannedModules) { module ->
                PlannedModuleCard(module)
            }
        }
    }
}

@Composable
private fun PlannedModuleCard(module: PlannedModule) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceContainerLow,
        ),
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(module.title, style = MaterialTheme.typography.titleMedium)
            Text(
                text = module.summary,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

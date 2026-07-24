package com.graduateentrance.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.List
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.graduateentrance.app.network.PaperAnnotationDto
import com.graduateentrance.app.network.PaperBlockDto
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.launch

private val annotationColors = listOf(
    "yellow" to Color(0xFFFFF59D),
    "green" to Color(0xFFC8E6C9),
    "blue" to Color(0xFFBBDEFB),
    "red" to Color(0xFFFFCDD2),
)

private fun highlightColor(name: String): Color =
    annotationColors.firstOrNull { it.first == name }?.second ?: annotationColors[0].second

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PaperReaderScreen(
    state: ReaderState,
    onClose: () -> Unit,
    onSaveProgress: (Int) -> Unit,
    onAddAnnotation: (blockIndex: Int, excerpt: String, note: String, color: String) -> Unit,
    onUpdateAnnotation: (annotationId: String, note: String?, color: String?) -> Unit,
    onDeleteAnnotation: (annotationId: String) -> Unit,
) {
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()
    var showToc by remember { mutableStateOf(false) }
    var annotationTarget by remember { mutableStateOf<Int?>(null) }

    LaunchedEffect(state.blocks.isNotEmpty()) {
        if (state.blocks.isNotEmpty() && state.initialBlockIndex > 0) {
            listState.scrollToItem(state.initialBlockIndex.coerceAtMost(state.blocks.size - 1))
        }
    }

    LaunchedEffect(state.blocks.isNotEmpty()) {
        if (state.blocks.isEmpty()) return@LaunchedEffect
        snapshotFlow { listState.firstVisibleItemIndex }
            .distinctUntilChanged()
            .collect { onSaveProgress(it) }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = state.paper.title,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.titleMedium,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onClose) {
                        Icon(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = "返回")
                    }
                },
                actions = {
                    if (state.toc.isNotEmpty()) {
                        IconButton(onClick = { showToc = true }) {
                            Icon(Icons.AutoMirrored.Outlined.List, contentDescription = "目录")
                        }
                    }
                },
            )
        },
    ) { innerPadding ->
        when {
            state.loading -> AppLoading(
                label = "正在加载正文",
                modifier = Modifier.padding(innerPadding),
            )
            state.error != null -> Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                AppNotice(state.error, NoticeTone.ERROR)
                Button(onClick = onClose, modifier = Modifier.fillMaxWidth()) {
                    Text("返回列表")
                }
            }
            else -> LazyColumn(
                state = listState,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(
                    horizontal = 20.dp,
                    vertical = 16.dp,
                ),
            ) {
                items(
                    count = state.blocks.size,
                    key = { it },
                ) { index ->
                    ReaderBlock(
                        block = state.blocks[index],
                        annotations = state.annotations.filter { it.blockIndex == index },
                        onLongClick = { annotationTarget = index },
                    )
                }
            }
        }
    }

    if (showToc) {
        ModalBottomSheet(onDismissRequest = { showToc = false }) {
            LazyColumn(
                modifier = Modifier.padding(bottom = 24.dp),
            ) {
                items(count = state.toc.size, key = { it }) { index ->
                    val entry = state.toc[index]
                    Text(
                        text = entry.title,
                        style = if (entry.level <= 2) {
                            MaterialTheme.typography.titleSmall
                        } else {
                            MaterialTheme.typography.bodyMedium
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable {
                                showToc = false
                                scope.launch {
                                    listState.scrollToItem(
                                        entry.blockIndex.coerceAtMost(state.blocks.size - 1),
                                    )
                                }
                            }
                            .padding(
                                start = (16 + (entry.level - 1).coerceAtLeast(0) * 16).dp,
                                end = 16.dp,
                                top = 10.dp,
                                bottom = 10.dp,
                            ),
                    )
                }
            }
        }
    }

    annotationTarget?.let { blockIndex ->
        val block = state.blocks.getOrNull(blockIndex)
        if (block != null) {
            AnnotationSheet(
                block = block,
                annotations = state.annotations.filter { it.blockIndex == blockIndex },
                onDismiss = { annotationTarget = null },
                onAdd = { note, color ->
                    onAddAnnotation(blockIndex, block.md.take(120), note, color)
                    annotationTarget = null
                },
                onUpdate = onUpdateAnnotation,
                onDelete = onDeleteAnnotation,
            )
        }
    }
}

@Composable
private fun ReaderBlock(
    block: PaperBlockDto,
    annotations: List<PaperAnnotationDto>,
    onLongClick: () -> Unit,
) {
    val highlighted = annotations.isNotEmpty()
    val background = if (highlighted) {
        highlightColor(annotations.first().color).copy(alpha = 0.45f)
    } else {
        Color.Transparent
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(6.dp))
            .background(background)
            .padding(vertical = if (block.type == "heading") 10.dp else 6.dp),
    ) {
        if (block.type == "heading") {
            Text(
                text = block.md,
                style = when (block.level ?: 2) {
                    1 -> MaterialTheme.typography.headlineSmall
                    2 -> MaterialTheme.typography.titleLarge
                    else -> MaterialTheme.typography.titleMedium
                },
                fontWeight = FontWeight.SemiBold,
            )
        } else {
            MarkdownText(
                markdown = block.md,
                style = MaterialTheme.typography.bodyLarge.copy(
                    fontSize = 17.sp,
                    lineHeight = 28.sp,
                ),
                onLongClick = onLongClick,
            )
        }
        annotations.filter { it.note.isNotBlank() }.forEach { annotation ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Surface(
                    color = highlightColor(annotation.color),
                    shape = CircleShape,
                    modifier = Modifier.size(10.dp),
                ) {}
                Spacer(Modifier.width(8.dp))
                Text(
                    text = annotation.note,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AnnotationSheet(
    block: PaperBlockDto,
    annotations: List<PaperAnnotationDto>,
    onDismiss: () -> Unit,
    onAdd: (note: String, color: String) -> Unit,
    onUpdate: (annotationId: String, note: String?, color: String?) -> Unit,
    onDelete: (annotationId: String) -> Unit,
) {
    var note by remember { mutableStateOf("") }
    var color by remember { mutableStateOf("yellow") }

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp)
                .padding(bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("标注这一段", style = MaterialTheme.typography.titleMedium)
            Text(
                text = block.md,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
            )
            annotations.forEach { annotation ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Surface(
                        color = highlightColor(annotation.color),
                        shape = CircleShape,
                        modifier = Modifier
                            .size(14.dp)
                            .clickable {
                                val names = annotationColors.map { it.first }
                                val next =
                                    names[(names.indexOf(annotation.color) + 1) % names.size]
                                onUpdate(annotation.id, null, next)
                            },
                    ) {}
                    Spacer(Modifier.width(10.dp))
                    Text(
                        text = annotation.note.ifBlank { "（无批注）" },
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.weight(1f),
                    )
                    IconButton(onClick = { onDelete(annotation.id) }) {
                        Icon(Icons.Outlined.Delete, contentDescription = "删除标注")
                    }
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                annotationColors.forEach { (name, tint) ->
                    Surface(
                        color = tint,
                        shape = CircleShape,
                        modifier = Modifier
                            .size(32.dp)
                            .clickable { color = name },
                    ) {
                        if (color == name) {
                            Icon(
                                Icons.Outlined.Check,
                                contentDescription = name,
                                modifier = Modifier.padding(6.dp),
                            )
                        }
                    }
                }
            }
            OutlinedTextField(
                value = note,
                onValueChange = { note = it },
                label = { Text("批注（可留空只做高亮）") },
                modifier = Modifier.fillMaxWidth(),
                minLines = 2,
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
            ) {
                TextButton(onClick = onDismiss) { Text("取消") }
                Spacer(Modifier.width(8.dp))
                Button(onClick = { onAdd(note.trim(), color) }) { Text("保存标注") }
            }
            Spacer(Modifier.height(4.dp))
        }
    }
}

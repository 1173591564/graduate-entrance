package com.graduateentrance.app.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.TextFields
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.nestedscroll.NestedScrollConnection
import androidx.compose.ui.input.nestedscroll.NestedScrollSource
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.graduateentrance.app.data.AppSettings
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

/** A self-contained reading palette so the reader feels like paper, independent of app theme. */
private data class ReaderPalette(
    val key: String,
    val label: String,
    val background: Color,
    val text: Color,
    val muted: Color,
    val accent: Color,
    val divider: Color,
    val chrome: Color,
)

private val readerPalettes = listOf(
    ReaderPalette(
        key = "paper",
        label = "纸张",
        background = Color(0xFFF4ECD8),
        text = Color(0xFF4A3F35),
        muted = Color(0xFF9A8C74),
        accent = Color(0xFFB07D46),
        divider = Color(0x33796F58),
        chrome = Color(0xFFEFE5CD),
    ),
    ReaderPalette(
        key = "plain",
        label = "素白",
        background = Color(0xFFFFFFFF),
        text = Color(0xFF1F2124),
        muted = Color(0xFF7A8087),
        accent = Color(0xFF245EA8),
        divider = Color(0x1F000000),
        chrome = Color(0xFFF6F7F9),
    ),
    ReaderPalette(
        key = "night",
        label = "夜间",
        background = Color(0xFF14130F),
        text = Color(0xFFCFC6B6),
        muted = Color(0xFF7F776A),
        accent = Color(0xFFC69A66),
        divider = Color(0x24CFC6B6),
        chrome = Color(0xFF1E1C17),
    ),
)

private fun paletteFor(key: String): ReaderPalette =
    readerPalettes.firstOrNull { it.key == key } ?: readerPalettes.first()

private fun estimateMinutes(blocks: List<PaperBlockDto>): Int {
    val words = blocks.sumOf { block -> block.md.split(Regex("\\s+")).count { it.isNotBlank() } }
    return (words / 200.0).let { if (it < 1) 1 else Math.round(it).toInt() }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PaperReaderScreen(
    state: ReaderState,
    onClose: () -> Unit,
    onSaveProgress: (Int) -> Unit,
    onAddAnnotation: (blockIndex: Int, excerpt: String, note: String, color: String) -> Unit,
    onUpdateAnnotation: (annotationId: String, note: String?, color: String?) -> Unit,
    onDeleteAnnotation: (annotationId: String) -> Unit,
    onMarkDone: () -> Unit = {},
) {
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()
    var showToc by remember { mutableStateOf(false) }
    var showTypeSheet by remember { mutableStateOf(false) }
    var annotationTarget by remember { mutableStateOf<Int?>(null) }
    var chromeVisible by remember { mutableStateOf(true) }
    var markedDone by remember { mutableStateOf(state.paper.status == "done") }

    var fontScale by remember { mutableFloatStateOf(AppSettings.readerFontScale) }
    var paletteKey by remember { mutableStateOf(AppSettings.readerTheme) }
    val palette = paletteFor(paletteKey)

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

    // Hide the chrome while reading forward, reveal it when scrolling back or at the top.
    val nestedScroll = remember {
        object : NestedScrollConnection {
            override fun onPreScroll(available: Offset, source: NestedScrollSource): Offset {
                if (available.y < -6f) chromeVisible = false
                else if (available.y > 6f) chromeVisible = true
                return Offset.Zero
            }
        }
    }
    LaunchedEffect(listState) {
        snapshotFlow { listState.firstVisibleItemIndex }
            .collect { if (it == 0) chromeVisible = true }
    }

    val progress by remember(state.blocks.size) {
        derivedStateOf {
            val total = state.blocks.size
            if (total <= 1) {
                if (state.loading) 0f else 1f
            } else {
                (listState.firstVisibleItemIndex.toFloat() / (total - 1)).coerceIn(0f, 1f)
            }
        }
    }
    val minutes = remember(state.blocks) { estimateMinutes(state.blocks) }

    Box(modifier = Modifier.fillMaxSize().background(palette.background)) {
        when {
            state.loading -> ReaderMessage("正在翻开这一篇…", palette)
            state.error != null -> ReaderError(state.error, palette, onClose)
            else -> LazyColumn(
                state = listState,
                modifier = Modifier
                    .fillMaxSize()
                    .nestedScroll(nestedScroll),
                contentPadding = PaddingValues(
                    start = 26.dp,
                    end = 26.dp,
                    top = 72.dp,
                    bottom = 96.dp,
                ),
            ) {
                item(key = "cover") {
                    ReaderCover(
                        category = state.paper.category,
                        title = state.paper.title,
                        minutes = minutes,
                        blocks = state.blocks.size,
                        palette = palette,
                    )
                }
                items(count = state.blocks.size, key = { it }) { index ->
                    ReaderBlock(
                        block = state.blocks[index],
                        annotations = state.annotations.filter { it.blockIndex == index },
                        palette = palette,
                        fontScale = fontScale,
                        onLongClick = { annotationTarget = index },
                    )
                }
                item(key = "colophon") {
                    ReaderColophon(
                        palette = palette,
                        done = markedDone,
                        onMarkDone = {
                            markedDone = true
                            onMarkDone()
                        },
                    )
                }
            }
        }

        // Top chrome: minimal bar + hairline reading progress.
        AnimatedVisibility(
            visible = chromeVisible,
            modifier = Modifier.align(Alignment.TopCenter),
            enter = slideInVertically { -it },
            exit = slideOutVertically { -it },
        ) {
            Column(modifier = Modifier.fillMaxWidth().background(palette.chrome)) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 6.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    ReaderIconButton(Icons.AutoMirrored.Outlined.ArrowBack, "返回", palette, onClose)
                    Text(
                        text = state.paper.title,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.labelLarge,
                        color = palette.muted,
                        modifier = Modifier.weight(1f).padding(horizontal = 4.dp),
                    )
                    ReaderIconButton(Icons.Outlined.TextFields, "版式", palette) { showTypeSheet = true }
                    if (state.toc.isNotEmpty()) {
                        ReaderIconButton(Icons.AutoMirrored.Outlined.List, "目录", palette) {
                            showToc = true
                        }
                    }
                }
                LinearProgressIndicator(
                    progress = { progress },
                    modifier = Modifier.fillMaxWidth().height(2.dp),
                    color = palette.accent,
                    trackColor = palette.divider,
                )
            }
        }

        // Bottom chrome: book-like position readout.
        AnimatedVisibility(
            visible = chromeVisible && !state.loading && state.error == null,
            modifier = Modifier.align(Alignment.BottomCenter),
            enter = slideInVertically { it },
            exit = slideOutVertically { it },
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(palette.chrome)
                    .padding(horizontal = 22.dp, vertical = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "${(progress * 100).toInt()}%",
                    style = MaterialTheme.typography.labelLarge,
                    color = palette.text,
                )
                Text(
                    text = "约 $minutes 分钟 · ${state.blocks.size} 段",
                    style = MaterialTheme.typography.labelMedium,
                    color = palette.muted,
                )
            }
        }
    }

    if (showToc) {
        ModalBottomSheet(
            onDismissRequest = { showToc = false },
            containerColor = palette.chrome,
        ) {
            Text(
                text = "目录",
                style = MaterialTheme.typography.titleMedium,
                color = palette.text,
                modifier = Modifier.padding(start = 20.dp, bottom = 4.dp),
            )
            LazyColumn(modifier = Modifier.padding(bottom = 24.dp)) {
                items(count = state.toc.size, key = { it }) { index ->
                    val entry = state.toc[index]
                    Text(
                        text = entry.title,
                        style = if (entry.level <= 2) {
                            MaterialTheme.typography.titleSmall
                        } else {
                            MaterialTheme.typography.bodyMedium
                        },
                        color = if (entry.level <= 2) palette.text else palette.muted,
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
                                start = (20 + (entry.level - 1).coerceAtLeast(0) * 16).dp,
                                end = 20.dp,
                                top = 11.dp,
                                bottom = 11.dp,
                            ),
                    )
                }
            }
        }
    }

    if (showTypeSheet) {
        TypeSettingsSheet(
            palette = palette,
            fontScale = fontScale,
            onFontScale = {
                fontScale = it
                AppSettings.readerFontScale = it
            },
            onPalette = {
                paletteKey = it
                AppSettings.readerTheme = it
            },
            onDismiss = { showTypeSheet = false },
        )
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
private fun ReaderIconButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    contentDescription: String,
    palette: ReaderPalette,
    onClick: () -> Unit,
) {
    IconButton(onClick = onClick) {
        Icon(icon, contentDescription = contentDescription, tint = palette.muted)
    }
}

@Composable
private fun ReaderCover(
    category: String,
    title: String,
    minutes: Int,
    blocks: Int,
    palette: ReaderPalette,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 24.dp, bottom = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = category.uppercase(),
            style = MaterialTheme.typography.labelMedium.copy(letterSpacing = 3.sp),
            color = palette.accent,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(16.dp))
        Text(
            text = title,
            style = MaterialTheme.typography.headlineSmall.copy(
                fontFamily = FontFamily.Serif,
                fontWeight = FontWeight.Bold,
                fontSize = 27.sp,
                lineHeight = 36.sp,
            ),
            color = palette.text,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(20.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.width(28.dp).height(1.dp).background(palette.divider))
            Text(
                text = "  约 $minutes 分钟 · $blocks 段  ",
                style = MaterialTheme.typography.labelMedium,
                color = palette.muted,
            )
            Box(Modifier.width(28.dp).height(1.dp).background(palette.divider))
        }
    }
}

@Composable
private fun ReaderColophon(
    palette: ReaderPalette,
    done: Boolean,
    onMarkDone: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 36.dp, bottom = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "· 全文完 ·",
            style = MaterialTheme.typography.titleMedium.copy(fontFamily = FontFamily.Serif),
            color = palette.muted,
        )
        Spacer(Modifier.height(20.dp))
        Surface(
            shape = RoundedCornerShape(24.dp),
            color = if (done) Color.Transparent else palette.accent,
            border = if (done) {
                androidx.compose.foundation.BorderStroke(1.dp, palette.divider)
            } else {
                null
            },
            modifier = Modifier.clickable(enabled = !done, onClick = onMarkDone),
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 22.dp, vertical = 11.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    Icons.Outlined.CheckCircle,
                    contentDescription = null,
                    tint = if (done) palette.muted else palette.background,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    text = if (done) "已读完" else "读完了，标为已读",
                    style = MaterialTheme.typography.labelLarge,
                    color = if (done) palette.muted else palette.background,
                )
            }
        }
    }
}

@Composable
private fun ReaderBlock(
    block: PaperBlockDto,
    annotations: List<PaperAnnotationDto>,
    palette: ReaderPalette,
    fontScale: Float,
    onLongClick: () -> Unit,
) {
    val highlighted = annotations.isNotEmpty()
    val background = if (highlighted) {
        highlightColor(annotations.first().color).copy(alpha = 0.32f)
    } else {
        Color.Transparent
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(6.dp))
            .background(background)
            .padding(
                horizontal = if (highlighted) 8.dp else 0.dp,
                vertical = if (block.type == "heading") 14.dp else 9.dp,
            ),
    ) {
        if (block.type == "heading") {
            val level = block.level ?: 2
            Text(
                text = block.md,
                style = when (level) {
                    1 -> MaterialTheme.typography.headlineSmall
                    2 -> MaterialTheme.typography.titleLarge
                    else -> MaterialTheme.typography.titleMedium
                }.copy(fontFamily = FontFamily.Serif),
                fontWeight = FontWeight.Bold,
                color = palette.text,
            )
        } else {
            MarkdownText(
                markdown = block.md,
                style = MaterialTheme.typography.bodyLarge.copy(
                    color = palette.text,
                    fontSize = (18 * fontScale).sp,
                ),
                serif = true,
                lineSpacingMultiplier = 1.55f,
                justify = true,
                onLongClick = onLongClick,
            )
        }
        annotations.filter { it.note.isNotBlank() }.forEach { annotation ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp),
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
                    color = palette.muted,
                )
            }
        }
    }
}

@Composable
private fun ReaderMessage(text: String, palette: ReaderPalette) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Text(text = text, style = MaterialTheme.typography.bodyMedium, color = palette.muted)
    }
}

@Composable
private fun ReaderError(text: String, palette: ReaderPalette, onClose: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(text = text, style = MaterialTheme.typography.bodyMedium, color = palette.text)
        Spacer(Modifier.height(16.dp))
        TextButton(onClick = onClose) { Text("返回书架", color = palette.accent) }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TypeSettingsSheet(
    palette: ReaderPalette,
    fontScale: Float,
    onFontScale: (Float) -> Unit,
    onPalette: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = palette.chrome) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp)
                .padding(bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp),
        ) {
            Text("阅读版式", style = MaterialTheme.typography.titleMedium, color = palette.text)
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("字号", style = MaterialTheme.typography.labelLarge, color = palette.muted)
                    Text(
                        text = "${(fontScale * 100).toInt()}%",
                        style = MaterialTheme.typography.labelLarge,
                        color = palette.text,
                    )
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("A", style = MaterialTheme.typography.bodyMedium, color = palette.muted)
                    Slider(
                        value = fontScale,
                        onValueChange = onFontScale,
                        valueRange = 0.8f..1.6f,
                        steps = 7,
                        modifier = Modifier.weight(1f).padding(horizontal = 8.dp),
                    )
                    Text("A", style = MaterialTheme.typography.titleLarge, color = palette.text)
                }
            }
            Text("背景", style = MaterialTheme.typography.labelLarge, color = palette.muted)
            Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                readerPalettes.forEach { option ->
                    val selected = option.key == palette.key
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Surface(
                            shape = CircleShape,
                            color = option.background,
                            border = androidx.compose.foundation.BorderStroke(
                                width = if (selected) 2.dp else 1.dp,
                                color = if (selected) palette.accent else palette.divider,
                            ),
                            modifier = Modifier
                                .size(48.dp)
                                .clickable { onPalette(option.key) },
                        ) {
                            if (selected) {
                                Icon(
                                    Icons.Outlined.Check,
                                    contentDescription = option.label,
                                    tint = option.text,
                                    modifier = Modifier.padding(13.dp),
                                )
                            }
                        }
                        Spacer(Modifier.height(6.dp))
                        Text(
                            text = option.label,
                            style = MaterialTheme.typography.labelSmall,
                            color = if (selected) palette.text else palette.muted,
                        )
                    }
                }
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
                androidx.compose.material3.Button(onClick = { onAdd(note.trim(), color) }) {
                    Text("保存标注")
                }
            }
            Spacer(Modifier.height(4.dp))
        }
    }
}

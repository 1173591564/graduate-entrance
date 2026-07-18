package com.graduateentrance.app.ui

import android.graphics.Bitmap
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.rememberTransformableState
import androidx.compose.foundation.gestures.transformable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.outlined.AutoStories
import androidx.compose.material.icons.outlined.ViewDay
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

private class PdfDocument(file: File) {
    private val descriptor =
        ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
    private val renderer = PdfRenderer(descriptor)
    private val mutex = Mutex()

    val pageCount: Int = renderer.pageCount

    suspend fun renderPage(index: Int, targetWidth: Int): Bitmap =
        withContext(Dispatchers.IO) {
            mutex.withLock {
                renderer.openPage(index).use { page ->
                    val width = targetWidth.coerceIn(1, 2160)
                    val height = (width.toFloat() * page.height / page.width).toInt()
                        .coerceAtLeast(1)
                    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                    bitmap.eraseColor(android.graphics.Color.WHITE)
                    page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    bitmap
                }
            }
        }

    fun close() {
        renderer.close()
        descriptor.close()
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PdfViewerScreen(
    file: File,
    title: String,
    onClose: () -> Unit,
) {
    val document = remember(file) {
        runCatching { PdfDocument(file) }.getOrNull()
    }
    DisposableEffect(document) {
        onDispose { document?.close() }
    }

    var scale by remember { mutableFloatStateOf(1f) }
    val transformState = rememberTransformableState { zoomChange, _, _ ->
        scale = (scale * zoomChange).coerceIn(1f, 3f)
    }
    var pagerMode by rememberSaveable { mutableStateOf(false) }
    var lastPage by rememberSaveable { mutableIntStateOf(0) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(title, maxLines = 1, overflow = TextOverflow.Ellipsis)
                },
                navigationIcon = {
                    IconButton(onClick = onClose) {
                        Icon(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = "返回")
                    }
                },
                actions = {
                    IconButton(onClick = {
                        scale = 1f
                        pagerMode = !pagerMode
                    }) {
                        Icon(
                            if (pagerMode) Icons.Outlined.ViewDay else Icons.Outlined.AutoStories,
                            contentDescription = if (pagerMode) "切换为滚动模式" else "切换为书页模式",
                        )
                    }
                },
            )
        },
    ) { innerPadding ->
        if (document == null) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
                contentAlignment = Alignment.Center,
            ) {
                Text("PDF 打开失败，文件可能已损坏")
            }
            return@Scaffold
        }
        val density = LocalDensity.current
        val targetWidth = with(density) { 420.dp.toPx() }.toInt() * 2
        var currentPage by remember { mutableIntStateOf(lastPage + 1) }
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
        ) {
            if (pagerMode) {
                val pagerState = rememberPagerState(
                    initialPage = lastPage.coerceIn(0, document.pageCount - 1),
                ) { document.pageCount }
                LaunchedEffect(pagerState.currentPage) {
                    lastPage = pagerState.currentPage
                    currentPage = pagerState.currentPage + 1
                }
                HorizontalPager(
                    state = pagerState,
                    modifier = Modifier
                        .fillMaxSize()
                        .background(MaterialTheme.colorScheme.surfaceVariant)
                        .transformable(transformState)
                        .graphicsLayer(scaleX = scale, scaleY = scale),
                ) { pageIndex ->
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState()),
                        contentAlignment = Alignment.Center,
                    ) {
                        PdfPage(
                            document = document,
                            pageIndex = pageIndex,
                            targetWidth = targetWidth,
                        )
                    }
                }
            } else {
                val listState = rememberLazyListState(
                    initialFirstVisibleItemIndex = lastPage.coerceIn(0, document.pageCount - 1),
                )
                val firstVisible by remember {
                    derivedStateOf { listState.firstVisibleItemIndex }
                }
                LaunchedEffect(firstVisible) {
                    lastPage = firstVisible
                    currentPage = firstVisible + 1
                }
                LazyColumn(
                    state = listState,
                    modifier = Modifier
                        .fillMaxSize()
                        .background(MaterialTheme.colorScheme.surfaceVariant)
                        .transformable(transformState)
                        .graphicsLayer(scaleX = scale, scaleY = scale),
                ) {
                    items((0 until document.pageCount).toList()) { pageIndex ->
                        PdfPage(
                            document = document,
                            pageIndex = pageIndex,
                            targetWidth = targetWidth,
                        )
                    }
                }
            }
            Surface(
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(16.dp),
                shape = RoundedCornerShape(999.dp),
                color = MaterialTheme.colorScheme.surface.copy(alpha = 0.85f),
                contentColor = MaterialTheme.colorScheme.onSurface,
            ) {
                Text(
                    text = "$currentPage / ${document.pageCount}",
                    style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                )
            }
        }
    }
}

@Composable
private fun PdfPage(
    document: PdfDocument,
    pageIndex: Int,
    targetWidth: Int,
) {
    var bitmap by remember(pageIndex) { mutableStateOf<Bitmap?>(null) }
    LaunchedEffect(document, pageIndex) {
        if (bitmap == null) {
            bitmap = runCatching { document.renderPage(pageIndex, targetWidth) }.getOrNull()
        }
    }
    val rendered = bitmap
    if (rendered != null) {
        Image(
            bitmap = rendered.asImageBitmap(),
            contentDescription = "第 ${pageIndex + 1} 页",
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 6.dp)
                .background(Color.White),
            contentScale = ContentScale.FillWidth,
        )
    } else {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(0.72f)
                .padding(bottom = 6.dp)
                .background(Color.White),
            contentAlignment = Alignment.Center,
        ) {
            CircularProgressIndicator(
                modifier = Modifier.size(28.dp),
                strokeWidth = 3.dp,
            )
        }
    }
}

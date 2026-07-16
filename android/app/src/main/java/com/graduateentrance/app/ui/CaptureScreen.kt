package com.graduateentrance.app.ui

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.outlined.AddPhotoAlternate
import androidx.compose.material.icons.outlined.AutoAwesome
import androidx.compose.material.icons.outlined.BrokenImage
import androidx.compose.material.icons.outlined.CameraAlt
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.CloudUpload
import androidx.compose.material.icons.outlined.PhotoLibrary
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private val captureKinds = listOf("wrong" to "错题", "hard" to "难题", "good" to "好题")

private fun newCameraUri(context: Context): Uri {
    val directory = File(context.cacheDir, "captures").apply { mkdirs() }
    val file = File.createTempFile("capture-", ".jpg", directory)
    return FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CaptureScreen(viewModel: CaptureViewModel) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val pendingCameraUri = remember { mutableStateOf<Uri?>(null) }
    val selectingEnabled = state.imageUris.size < MAX_CAPTURE_IMAGES &&
        !state.submitting &&
        !state.extracting

    val cameraLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.TakePicture(),
    ) { success ->
        val uri = pendingCameraUri.value
        if (success && uri != null) {
            viewModel.addImages(listOf(uri))
        }
        pendingCameraUri.value = null
    }
    val galleryLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.PickMultipleVisualMedia(MAX_CAPTURE_IMAGES),
    ) { uris ->
        if (uris.isNotEmpty()) {
            viewModel.addImages(uris)
        }
    }

    fun takePhoto() {
        val uri = newCameraUri(context)
        pendingCameraUri.value = uri
        cameraLauncher.launch(uri)
    }

    fun pickImages() {
        galleryLauncher.launch(
            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly),
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("快速拍题")
                        Text(
                            text = "拍下即走，识别自动完成",
                            style = MaterialTheme.typography.labelMedium,
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
            contentPadding = PaddingValues(horizontal = 18.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            state.notice?.let { notice ->
                item {
                    AppNotice(
                        text = notice,
                        tone = when {
                            "失败" in notice || "不可用" in notice -> NoticeTone.ERROR
                            "完成" in notice || "已上传" in notice -> NoticeTone.SUCCESS
                            else -> NoticeTone.INFO
                        },
                    )
                }
            }
            if (state.submitting || state.extracting) {
                item {
                    CaptureProgressCard(
                        uploading = state.submitting,
                        extracting = state.extracting,
                    )
                }
            }
            state.extraction?.let { extraction ->
                item {
                    ExtractionCard(
                        content = extraction.contentMd,
                        knowledgePoints = extraction.knowledgePoints.map {
                            it.knowledgePointName to it.role
                        },
                        solution = extraction.solution?.contentMd,
                        onDismiss = viewModel::dismissExtraction,
                    )
                }
            }
            if (state.imageUris.isEmpty()) {
                item {
                    CaptureHero(
                        onTakePhoto = ::takePhoto,
                        onPickImages = ::pickImages,
                        enabled = selectingEnabled,
                    )
                }
                item {
                    Text(
                        text = "支持一次上传 1–$MAX_CAPTURE_IMAGES 张图片，建议题面清晰、边缘完整。",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            } else {
                item {
                    CaptureStepHeader(
                        step = "1",
                        title = "检查图片",
                        description = "${state.imageUris.size} / $MAX_CAPTURE_IMAGES 张，可调整顺序",
                    )
                }
                item {
                    LazyRow(
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        contentPadding = PaddingValues(vertical = 2.dp),
                    ) {
                        itemsIndexed(
                            items = state.imageUris,
                            key = { _, uri -> uri.toString() },
                        ) { index, uri ->
                            ImagePreviewItem(
                                uri = uri,
                                index = index,
                                total = state.imageUris.size,
                                onMoveLeft = { viewModel.moveImage(uri, -1) },
                                onMoveRight = { viewModel.moveImage(uri, 1) },
                                onRemove = { viewModel.removeImage(uri) },
                            )
                        }
                    }
                }
                if (selectingEnabled) {
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp),
                        ) {
                            OutlinedButton(
                                onClick = ::takePhoto,
                                modifier = Modifier.weight(1f),
                            ) {
                                Icon(Icons.Outlined.CameraAlt, contentDescription = null)
                                Spacer(Modifier.width(6.dp))
                                Text("继续拍")
                            }
                            OutlinedButton(
                                onClick = ::pickImages,
                                modifier = Modifier.weight(1f),
                            ) {
                                Icon(Icons.Outlined.AddPhotoAlternate, contentDescription = null)
                                Spacer(Modifier.width(6.dp))
                                Text("继续选")
                            }
                        }
                    }
                }
                item {
                    CaptureStepHeader(
                        step = "2",
                        title = "补充信息",
                        description = "分类和备注均可稍后在 Web 审核台修改",
                    )
                }
                item {
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(captureKinds.size) { index ->
                            val (value, label) = captureKinds[index]
                            FilterChip(
                                selected = state.kind == value,
                                onClick = { viewModel.setKind(value) },
                                label = { Text(label) },
                            )
                        }
                    }
                }
                item {
                    OutlinedTextField(
                        value = state.note,
                        onValueChange = viewModel::setNote,
                        label = { Text("备注（可选）") },
                        placeholder = { Text("例如：二刷仍然卡住、注意边界条件") },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 3,
                        maxLines = 5,
                    )
                }
                item {
                    Button(
                        onClick = viewModel::submit,
                        enabled = !state.submitting && !state.extracting,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Icon(Icons.Outlined.CloudUpload, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("上传并开始 AI 识别")
                    }
                }
                item {
                    Text(
                        text = "上传后即可离开页面；识别结果会保留为草稿，定稿后进入复习计划。",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}

@Composable
private fun CaptureHero(
    onTakePhoto: () -> Unit,
    onPickImages: () -> Unit,
    enabled: Boolean,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer,
        ),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 22.dp, vertical = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Surface(
                shape = CircleShape,
                color = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
            ) {
                Icon(
                    imageVector = Icons.Outlined.CameraAlt,
                    contentDescription = null,
                    modifier = Modifier
                        .padding(18.dp)
                        .size(42.dp),
                )
            }
            Text("拍下题目，继续学习", style = MaterialTheme.typography.headlineSmall)
            Text(
                text = "题面提取、知识点归类和解法草稿将在后台完成",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.78f),
            )
            Button(
                onClick = onTakePhoto,
                enabled = enabled,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Outlined.CameraAlt, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("立即拍照")
            }
            OutlinedButton(
                onClick = onPickImages,
                enabled = enabled,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Outlined.PhotoLibrary, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("从相册选择")
            }
        }
    }
}

@Composable
private fun CaptureStepHeader(
    step: String,
    title: String,
    description: String,
) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Surface(
            shape = CircleShape,
            color = MaterialTheme.colorScheme.primaryContainer,
            contentColor = MaterialTheme.colorScheme.onPrimaryContainer,
        ) {
            Text(
                text = step,
                style = MaterialTheme.typography.labelLarge,
                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            )
        }
        Column {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(
                description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun CaptureProgressCard(uploading: Boolean, extracting: Boolean) {
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
            Row(
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Outlined.AutoAwesome, contentDescription = null)
                Text(
                    text = if (uploading) "正在安全上传图片" else "AI 正在提取题面与知识点",
                    style = MaterialTheme.typography.titleMedium,
                )
            }
            LinearProgressIndicator(
                progress = { if (uploading) 0.35f else if (extracting) 0.72f else 1f },
                modifier = Modifier.fillMaxWidth(),
            )
            Text(
                text = if (uploading) "上传完成后会自动进入识别阶段" else "可以切换页面，任务会继续执行",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun ExtractionCard(
    content: String,
    knowledgePoints: List<Pair<String, String>>,
    solution: String?,
    onDismiss: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(Icons.Outlined.AutoAwesome, contentDescription = null)
                    Text("AI 识别预览", style = MaterialTheme.typography.titleMedium)
                }
                TextButton(onClick = onDismiss) {
                    Text("收起")
                }
            }
            AppStatusChip("等待人工确认", NoticeTone.WARNING)
            Text(content, style = MaterialTheme.typography.bodyLarge)
            if (knowledgePoints.isNotEmpty()) {
                Text(
                    text = knowledgePoints.joinToString(" · ") { (name, role) ->
                        "$name（${if (role == "primary") "主" else "次"}）"
                    },
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
            solution?.let {
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surface,
                    ),
                ) {
                    Column(
                        modifier = Modifier.padding(14.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Text("解法草稿", style = MaterialTheme.typography.labelLarge)
                        Text(
                            text = it,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ImagePreviewItem(
    uri: Uri,
    index: Int,
    total: Int,
    onMoveLeft: () -> Unit,
    onMoveRight: () -> Unit,
    onRemove: () -> Unit,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Box {
            ImageThumbnail(uri = uri, index = index)
            Surface(
                modifier = Modifier.align(Alignment.TopEnd),
                shape = CircleShape,
                color = MaterialTheme.colorScheme.surface.copy(alpha = 0.9f),
            ) {
                IconButton(
                    onClick = onRemove,
                    modifier = Modifier.size(34.dp),
                ) {
                    Icon(
                        Icons.Outlined.Close,
                        contentDescription = "移除第 ${index + 1} 张图片",
                        modifier = Modifier.size(18.dp),
                    )
                }
            }
        }
        Row {
            IconButton(
                onClick = onMoveLeft,
                enabled = index > 0,
                modifier = Modifier.size(36.dp),
            ) {
                Icon(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = "图片前移")
            }
            Text(
                text = "${index + 1}",
                style = MaterialTheme.typography.labelLarge,
                modifier = Modifier.align(Alignment.CenterVertically),
            )
            IconButton(
                onClick = onMoveRight,
                enabled = index < total - 1,
                modifier = Modifier.size(36.dp),
            ) {
                Icon(Icons.AutoMirrored.Outlined.ArrowForward, contentDescription = "图片后移")
            }
        }
    }
}

@Composable
private fun ImageThumbnail(uri: Uri, index: Int) {
    val context = LocalContext.current
    var bitmap by remember(uri) { mutableStateOf<Bitmap?>(null) }
    LaunchedEffect(uri) {
        bitmap = withContext(Dispatchers.IO) {
            try {
                val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                context.contentResolver.openInputStream(uri)?.use { stream ->
                    BitmapFactory.decodeStream(stream, null, bounds)
                }
                val options = BitmapFactory.Options().apply {
                    inSampleSize = maxOf(1, bounds.outWidth / 360)
                }
                context.contentResolver.openInputStream(uri)?.use { stream ->
                    BitmapFactory.decodeStream(stream, null, options)
                }
            } catch (_: Exception) {
                null
            }
        }
    }
    bitmap?.let {
        Image(
            bitmap = it.asImageBitmap(),
            contentDescription = "待上传题目图片 ${index + 1}",
            contentScale = ContentScale.Crop,
            modifier = Modifier
                .size(118.dp)
                .clip(RoundedCornerShape(16.dp)),
        )
    } ?: Box(
        modifier = Modifier
            .size(118.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            Icons.Outlined.BrokenImage,
            contentDescription = "图片加载中",
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

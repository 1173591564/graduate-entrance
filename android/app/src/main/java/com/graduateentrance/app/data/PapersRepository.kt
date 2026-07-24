package com.graduateentrance.app.data

import com.graduateentrance.app.network.GraduateEntranceApi
import com.graduateentrance.app.network.PaperAnnotationCreateRequest
import com.graduateentrance.app.network.PaperAnnotationDto
import com.graduateentrance.app.network.PaperAnnotationUpdateRequest
import com.graduateentrance.app.network.PaperBlockDto
import com.graduateentrance.app.network.PaperDto
import com.graduateentrance.app.network.PaperGroupDto
import com.graduateentrance.app.network.PaperStatsDto
import com.graduateentrance.app.network.PaperStatusRequest
import com.graduateentrance.app.network.PaperTocEntryDto
import java.io.File
import java.io.IOException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException

sealed interface PapersLoadResult {
    data class Loaded(
        val today: PaperItem?,
        val groups: List<PaperGroup>,
        val stats: PaperStats,
    ) : PapersLoadResult
    data object Offline : PapersLoadResult
    data class Rejected(val code: Int) : PapersLoadResult
}

sealed interface PaperStatusResult {
    data class Updated(val paper: PaperItem) : PaperStatusResult
    data object Offline : PaperStatusResult
    data class Rejected(val code: Int) : PaperStatusResult
}

sealed interface PaperDownloadResult {
    data class Ready(val file: File) : PaperDownloadResult
    data object Offline : PaperDownloadResult
    data class Rejected(val code: Int) : PaperDownloadResult
}

sealed interface PaperContentResult {
    data class Loaded(
        val blocks: List<PaperContentBlock>,
        val toc: List<PaperContentTocEntry>,
        val annotations: List<PaperContentAnnotation>,
    ) : PaperContentResult
    data object Offline : PaperContentResult
    data class Rejected(val code: Int) : PaperContentResult
}

sealed interface PaperAnnotationResult {
    data class Saved(val annotation: PaperContentAnnotation) : PaperAnnotationResult
    data object Deleted : PaperAnnotationResult
    data object Offline : PaperAnnotationResult
    data class Rejected(val code: Int) : PaperAnnotationResult
}

data class PaperContentBlock(
    val type: String,
    val md: String,
    val level: Int,
)

data class PaperContentTocEntry(
    val title: String,
    val level: Int,
    val blockIndex: Int,
)

data class PaperContentAnnotation(
    val id: String,
    val paperId: String,
    val blockIndex: Int,
    val excerpt: String,
    val note: String,
    val color: String,
    val createdAt: String,
)

data class PaperItem(
    val id: String,
    val relPath: String,
    val title: String,
    val category: String,
    val sizeBytes: Long,
    val status: String,
    val hasFile: Boolean,
    val hasContent: Boolean,
    val startedOn: String?,
    val finishedOn: String?,
)

data class PaperGroup(
    val category: String,
    val papers: List<PaperItem>,
)

data class PaperStats(
    val totalCount: Int,
    val unreadCount: Int,
    val readingCount: Int,
    val doneCount: Int,
)

class PapersRepository(
    private val api: GraduateEntranceApi,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
) {
    suspend fun load(): PapersLoadResult =
        try {
            val today = api.papersToday()
            val list = api.papers()
            PapersLoadResult.Loaded(
                today = today.paper.toPaperItemOrNull(),
                groups = list.groups.orEmpty().mapNotNull { it.toPaperGroupOrNull() },
                stats = list.stats.toPaperStats(),
            )
        } catch (_: IOException) {
            PapersLoadResult.Offline
        } catch (error: HttpException) {
            PapersLoadResult.Rejected(error.code())
        }

    suspend fun setStatus(paperId: String, status: String): PaperStatusResult =
        try {
            api.setPaperStatus(paperId, PaperStatusRequest(status))
                .paper
                ?.toPaperItemOrNull()
                ?.let { PaperStatusResult.Updated(it) }
                ?: PaperStatusResult.Rejected(502)
        } catch (_: IOException) {
            PaperStatusResult.Offline
        } catch (error: HttpException) {
            PaperStatusResult.Rejected(error.code())
        }

    suspend fun download(paperId: String, target: File): PaperDownloadResult =
        withContext(ioDispatcher) {
            try {
                api.downloadPaper(paperId).use { body ->
                    target.parentFile?.mkdirs()
                    body.byteStream().use { input ->
                        target.outputStream().use { output -> input.copyTo(output) }
                    }
                }
                PaperDownloadResult.Ready(target)
            } catch (_: IOException) {
                PaperDownloadResult.Offline
            } catch (error: HttpException) {
                PaperDownloadResult.Rejected(error.code())
            }
        }

    suspend fun content(paperId: String): PaperContentResult =
        try {
            val content = api.paperContent(paperId)
            val annotations = api.paperAnnotations(paperId)
            PaperContentResult.Loaded(
                content.blocks.orEmpty()
                    .filterNotNull()
                    .mapNotNull { it.toContentBlockOrNull() },
                content.toc.orEmpty()
                    .filterNotNull()
                    .mapNotNull { it.toContentTocEntryOrNull() },
                annotations.annotations.orEmpty()
                    .filterNotNull()
                    .mapNotNull { it.toContentAnnotationOrNull() },
            )
        } catch (_: IOException) {
            PaperContentResult.Offline
        } catch (error: HttpException) {
            PaperContentResult.Rejected(error.code())
        }

    suspend fun addAnnotation(
        paperId: String,
        blockIndex: Int,
        excerpt: String,
        note: String,
        color: String,
    ): PaperAnnotationResult =
        try {
            PaperAnnotationResult.Saved(
                api.createPaperAnnotation(
                    paperId,
                    PaperAnnotationCreateRequest(blockIndex, excerpt, note, color),
                ).toContentAnnotation(),
            )
        } catch (_: IOException) {
            PaperAnnotationResult.Offline
        } catch (error: HttpException) {
            PaperAnnotationResult.Rejected(error.code())
        }

    suspend fun updateAnnotation(
        annotationId: String,
        note: String?,
        color: String?,
    ): PaperAnnotationResult =
        try {
            PaperAnnotationResult.Saved(
                api.updatePaperAnnotation(
                    annotationId,
                    PaperAnnotationUpdateRequest(note, color),
                ).toContentAnnotation(),
            )
        } catch (_: IOException) {
            PaperAnnotationResult.Offline
        } catch (error: HttpException) {
            PaperAnnotationResult.Rejected(error.code())
        }

    suspend fun deleteAnnotation(annotationId: String): PaperAnnotationResult =
        try {
            val response = api.deletePaperAnnotation(annotationId)
            if (response.isSuccessful) {
                PaperAnnotationResult.Deleted
            } else {
                PaperAnnotationResult.Rejected(response.code())
            }
        } catch (_: IOException) {
            PaperAnnotationResult.Offline
        } catch (error: HttpException) {
            PaperAnnotationResult.Rejected(error.code())
        }
}

private fun PaperDto?.toPaperItemOrNull(): PaperItem? {
    val paper = this ?: return null
    val id = paper.id?.trim().orEmpty()
    if (id.isBlank()) return null
    return PaperItem(
        id = id,
        relPath = paper.relPath?.trim().orEmpty(),
        title = paper.title?.trim().takeUnless { it.isNullOrBlank() } ?: "未命名论文",
        category = paper.category?.trim().takeUnless { it.isNullOrBlank() } ?: "未分类",
        sizeBytes = paper.sizeBytes ?: 0L,
        status = paper.status?.trim().takeUnless { it.isNullOrBlank() } ?: "unread",
        hasFile = paper.hasFile == true,
        hasContent = paper.hasContent == true,
        startedOn = paper.startedOn,
        finishedOn = paper.finishedOn,
    )
}

private fun PaperGroupDto.toPaperGroupOrNull(): PaperGroup? {
    val category = category?.trim().takeUnless { it.isNullOrBlank() } ?: "未分类"
    val papers = papers.orEmpty().mapNotNull { it.toPaperItemOrNull() }
    if (papers.isEmpty()) return null
    return PaperGroup(category, papers)
}

private fun PaperStatsDto?.toPaperStats(): PaperStats {
    val stats = this
    return PaperStats(
        totalCount = stats?.totalCount?.coerceAtLeast(0) ?: 0,
        unreadCount = stats?.unreadCount?.coerceAtLeast(0) ?: 0,
        readingCount = stats?.readingCount?.coerceAtLeast(0) ?: 0,
        doneCount = stats?.doneCount?.coerceAtLeast(0) ?: 0,
    )
}

private fun PaperBlockDto?.toContentBlockOrNull(): PaperContentBlock? {
    val block = this ?: return null
    val type = block.type?.trim().orEmpty()
    val md = block.md?.trim().orEmpty()
    if (type.isBlank() || md.isBlank()) return null
    return PaperContentBlock(type = type, md = md, level = block.level ?: 0)
}

private fun PaperTocEntryDto?.toContentTocEntryOrNull(): PaperContentTocEntry? {
    val entry = this ?: return null
    val title = entry.title?.trim().orEmpty()
    val level = entry.level ?: 0
    val blockIndex = entry.blockIndex ?: return null
    if (title.isBlank()) return null
    return PaperContentTocEntry(title = title, level = level, blockIndex = blockIndex)
}

private fun PaperAnnotationDto?.toContentAnnotationOrNull(): PaperContentAnnotation? {
    val annotation = this ?: return null
    val id = annotation.id?.trim().orEmpty()
    val paperId = annotation.paperId?.trim().orEmpty()
    val excerpt = annotation.excerpt?.trim().orEmpty()
    val note = annotation.note?.trim().orEmpty()
    val color = annotation.color?.trim().orEmpty()
    val createdAt = annotation.createdAt?.trim().orEmpty()
    val blockIndex = annotation.blockIndex ?: return null
    if (id.isBlank() || paperId.isBlank() || excerpt.isBlank() || color.isBlank() || createdAt.isBlank()) {
        return null
    }
    return PaperContentAnnotation(
        id = id,
        paperId = paperId,
        blockIndex = blockIndex,
        excerpt = excerpt,
        note = note,
        color = color,
        createdAt = createdAt,
    )
}

private fun PaperAnnotationDto.toContentAnnotation(): PaperContentAnnotation =
    PaperContentAnnotation(
        id = id.orEmpty(),
        paperId = paperId.orEmpty(),
        blockIndex = blockIndex ?: 0,
        excerpt = excerpt.orEmpty(),
        note = note.orEmpty(),
        color = color.orEmpty(),
        createdAt = createdAt.orEmpty(),
    )

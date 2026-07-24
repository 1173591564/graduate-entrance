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
        val today: PaperDto?,
        val groups: List<PaperGroupDto>,
        val stats: PaperStatsDto,
    ) : PapersLoadResult
    data object Offline : PapersLoadResult
    data class Rejected(val code: Int) : PapersLoadResult
}

sealed interface PaperStatusResult {
    data class Updated(val paper: PaperDto) : PaperStatusResult
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
        val blocks: List<PaperBlockDto>,
        val toc: List<PaperTocEntryDto>,
        val annotations: List<PaperAnnotationDto>,
    ) : PaperContentResult
    data object Offline : PaperContentResult
    data class Rejected(val code: Int) : PaperContentResult
}

sealed interface PaperAnnotationResult {
    data class Saved(val annotation: PaperAnnotationDto) : PaperAnnotationResult
    data object Deleted : PaperAnnotationResult
    data object Offline : PaperAnnotationResult
    data class Rejected(val code: Int) : PaperAnnotationResult
}

class PapersRepository(
    private val api: GraduateEntranceApi,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
) {
    suspend fun load(): PapersLoadResult =
        try {
            val today = api.papersToday()
            val list = api.papers()
            PapersLoadResult.Loaded(today.paper, list.groups, list.stats)
        } catch (_: IOException) {
            PapersLoadResult.Offline
        } catch (error: HttpException) {
            PapersLoadResult.Rejected(error.code())
        }

    suspend fun setStatus(paperId: String, status: String): PaperStatusResult =
        try {
            PaperStatusResult.Updated(
                api.setPaperStatus(paperId, PaperStatusRequest(status)).paper,
            )
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
                content.blocks.orEmpty(),
                content.toc.orEmpty(),
                annotations.annotations.orEmpty(),
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
                ),
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
                ),
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

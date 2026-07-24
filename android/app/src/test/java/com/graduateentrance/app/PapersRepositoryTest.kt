package com.graduateentrance.app

import com.graduateentrance.app.data.PaperDownloadResult
import com.graduateentrance.app.data.PaperStatusResult
import com.graduateentrance.app.data.PapersLoadResult
import com.graduateentrance.app.data.PaperContentResult
import com.graduateentrance.app.data.PapersRepository
import com.graduateentrance.app.network.ChatConversationListDto
import com.graduateentrance.app.network.ChatHistoryDto
import com.graduateentrance.app.network.ChatSendResultDto
import com.graduateentrance.app.network.DueReviewsDto
import com.graduateentrance.app.network.ExtractionResultDto
import com.graduateentrance.app.network.GraduateEntranceApi
import com.graduateentrance.app.network.PaperAnnotationCreateRequest
import com.graduateentrance.app.network.PaperAnnotationDto
import com.graduateentrance.app.network.PaperAnnotationListDto
import com.graduateentrance.app.network.PaperAnnotationUpdateRequest
import com.graduateentrance.app.network.PaperBlockDto
import com.graduateentrance.app.network.PaperContentDto
import com.graduateentrance.app.network.PaperTocEntryDto
import com.graduateentrance.app.network.PaperDto
import com.graduateentrance.app.network.PaperGroupDto
import com.graduateentrance.app.network.PaperListDto
import com.graduateentrance.app.network.PaperStatsDto
import com.graduateentrance.app.network.PaperStatusRequest
import com.graduateentrance.app.network.PaperStatusResultDto
import com.graduateentrance.app.network.PaperTodayDto
import com.graduateentrance.app.network.ProblemCreatedDto
import com.graduateentrance.app.network.RecitationListDto
import com.graduateentrance.app.network.RecitationTodayDto
import com.graduateentrance.app.network.ReciteRequest
import com.graduateentrance.app.network.ReciteResultDto
import com.graduateentrance.app.network.ReviewRequest
import com.graduateentrance.app.network.ReviewResultDto
import com.graduateentrance.app.network.ServiceStatus
import com.graduateentrance.app.network.TaskCompletionRequest
import com.graduateentrance.app.network.TaskUpdateRequest
import com.graduateentrance.app.network.TodayDto
import com.graduateentrance.app.network.TodayTaskDto
import com.graduateentrance.app.network.VocabDictationDto
import com.graduateentrance.app.network.VocabDictationResultDto
import com.graduateentrance.app.network.VocabDictationResultRequest
import com.graduateentrance.app.network.VocabGradeRequest
import com.graduateentrance.app.network.VocabGradeResultDto
import com.graduateentrance.app.network.VocabStatsDto
import com.graduateentrance.app.network.VocabTodayDto
import com.graduateentrance.app.network.VocabWordDto
import java.io.File
import java.io.IOException
import kotlinx.coroutines.test.runTest
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response

private fun paper(id: String, status: String = "unread") = PaperDto(
    id = id,
    relPath = "RAG/$id.pdf",
    title = "Paper $id",
    category = "RAG",
    sizeBytes = 1024,
    status = status,
    hasFile = true,
    startedOn = null,
    finishedOn = null,
)

private val emptyStats = PaperStatsDto(0, 0, 0, 0)

private class FakePapersApi : GraduateEntranceApi {

    var contentResponse: PaperContentDto? = null

    override suspend fun paperContent(paperId: String): PaperContentDto {
        maybeFail()
        return contentResponse ?: throw UnsupportedOperationException()
    }

    override suspend fun paperAnnotations(paperId: String): PaperAnnotationListDto {
        maybeFail()
        return PaperAnnotationListDto(emptyList())
    }

    override suspend fun createPaperAnnotation(
        paperId: String,
        payload: PaperAnnotationCreateRequest,
    ): PaperAnnotationDto = throw UnsupportedOperationException()

    override suspend fun updatePaperAnnotation(
        annotationId: String,
        payload: PaperAnnotationUpdateRequest,
    ): PaperAnnotationDto = throw UnsupportedOperationException()

    override suspend fun deletePaperAnnotation(annotationId: String): Response<Unit> =
        throw UnsupportedOperationException()
    var offline = false
    var rejectWith: Int? = null
    var listResponse = PaperListDto(emptyList(), emptyStats)
    var todayResponse = PaperTodayDto("2026-07-17", null, emptyStats)
    var pdfBytes: ByteArray = byteArrayOf(1, 2, 3)
    val statusUpdates = mutableListOf<Pair<String, String>>()

    override suspend fun ping(): ServiceStatus = ServiceStatus("ok", "test", "test")

    override suspend fun today(date: String): TodayDto = TodayDto(date, 0, 0, 0, emptyList())

    override suspend fun completeTask(taskId: String, payload: TaskCompletionRequest): TodayTaskDto =
        throw UnsupportedOperationException()

    override suspend fun updateTask(taskId: String, payload: TaskUpdateRequest): TodayTaskDto =
        throw UnsupportedOperationException()

    override suspend fun dueReviews(includeDrafts: Boolean, limit: Int): DueReviewsDto =
        DueReviewsDto(0, "2026-07-17", emptyList())

    override suspend fun reviewProblem(problemId: String, payload: ReviewRequest): ReviewResultDto =
        throw UnsupportedOperationException()

    override suspend fun submitProblem(
        kind: RequestBody,
        note: RequestBody,
        images: List<MultipartBody.Part>,
    ): ProblemCreatedDto = ProblemCreatedDto("p", "draft", emptyList())

    override suspend fun extractProblem(problemId: String): ExtractionResultDto =
        ExtractionResultDto(problemId, "test", "", emptyList(), null)

    private fun maybeFail() {
        if (offline) throw IOException("offline")
        rejectWith?.let { code ->
            throw HttpException(
                Response.error<PaperListDto>(
                    code,
                    "{}".toResponseBody("application/json".toMediaType()),
                ),
            )
        }
    }

    override suspend fun papers(): PaperListDto {
        maybeFail()
        return listResponse
    }

    override suspend fun papersToday(): PaperTodayDto {
        maybeFail()
        return todayResponse
    }

    override suspend fun setPaperStatus(
        paperId: String,
        payload: PaperStatusRequest,
    ): PaperStatusResultDto {
        maybeFail()
        statusUpdates.add(paperId to payload.status)
        return PaperStatusResultDto(paper(paperId, payload.status))
    }

    override suspend fun downloadPaper(paperId: String): ResponseBody {
        maybeFail()
        return pdfBytes.toResponseBody("application/pdf".toMediaType())
    }

    override suspend fun recitations(subject: String?): RecitationListDto =
        throw UnsupportedOperationException()

    override suspend fun recitationToday(subject: String?): RecitationTodayDto =
        throw UnsupportedOperationException()

    override suspend fun reciteItem(itemId: String, payload: ReciteRequest): ReciteResultDto =
        throw UnsupportedOperationException()

    override suspend fun vocabToday(newLimit: Int): VocabTodayDto = throw UnsupportedOperationException()

    override suspend fun gradeVocabWord(
        wordId: String,
        payload: VocabGradeRequest,
    ): VocabGradeResultDto = throw UnsupportedOperationException()

    override suspend fun vocabDictation(): VocabDictationDto = throw UnsupportedOperationException()

    override suspend fun submitVocabDictationResult(
        payload: VocabDictationResultRequest,
    ): VocabDictationResultDto = throw UnsupportedOperationException()

    override suspend fun enrichVocabWord(wordId: String): VocabWordDto =
        throw UnsupportedOperationException()

    override suspend fun vocabStats(): VocabStatsDto = throw UnsupportedOperationException()

    override suspend fun chatConversations(): ChatConversationListDto =
        throw UnsupportedOperationException()

    override suspend fun chatHistory(conversationId: String): ChatHistoryDto =
        throw UnsupportedOperationException()

    override suspend fun deleteChatConversation(conversationId: String): Response<Unit> =
        throw UnsupportedOperationException()

    override suspend fun sendChatMessage(
        conversationId: RequestBody?,
        content: RequestBody,
        images: List<MultipartBody.Part>,
    ): ChatSendResultDto = throw UnsupportedOperationException()
}

class PapersRepositoryTest {
    @Test
    fun loadReturnsTodayGroupsAndStats() = runTest {
        val api = FakePapersApi()
        val stats = PaperStatsDto(2, 1, 1, 0)
        api.todayResponse = PaperTodayDto("2026-07-17", paper("p1", "reading"), stats)
        api.listResponse = PaperListDto(
            listOf(PaperGroupDto("RAG", listOf(paper("p1", "reading"), paper("p2")))),
            stats,
        )
        val repository = PapersRepository(api)

        val result = repository.load()

        assertTrue(result is PapersLoadResult.Loaded)
        result as PapersLoadResult.Loaded
        assertEquals("p1", result.today?.id)
        assertEquals(listOf("RAG"), result.groups.map { it.category })
        assertEquals(2, result.stats.totalCount)
    }

    @Test
    fun contentReturnsBlocksTocAndAnnotations() = runTest {
        val api = FakePapersApi()
        api.contentResponse = PaperContentDto(
            paper = paper("p1", "reading"),
            source = "ar5iv",
            blocks = listOf(
                PaperBlockDto(type = "heading", md = "Intro", level = 2),
                PaperBlockDto(type = "paragraph", md = "Body \$x\$"),
            ),
            toc = listOf(PaperTocEntryDto(title = "Intro", level = 2, blockIndex = 0)),
        )

        val result = PapersRepository(api).content("p1")

        assertTrue(result is PaperContentResult.Loaded)
        result as PaperContentResult.Loaded
        assertEquals(2, result.blocks.size)
        assertEquals(0, result.toc.single().blockIndex)
        assertTrue(result.annotations.isEmpty())
    }

    @Test
    fun contentReportsRejection() = runTest {
        val api = FakePapersApi()
        api.rejectWith = 404

        val result = PapersRepository(api).content("p1")

        assertTrue(result is PaperContentResult.Rejected)
        result as PaperContentResult.Rejected
        assertEquals(404, result.code)
    }

    @Test
    fun loadReportsOffline() = runTest {
        val api = FakePapersApi()
        api.offline = true

        assertTrue(PapersRepository(api).load() is PapersLoadResult.Offline)
    }

    @Test
    fun setStatusSubmitsAndReturnsPaper() = runTest {
        val api = FakePapersApi()
        val repository = PapersRepository(api)

        val result = repository.setStatus("p1", "done")

        assertTrue(result is PaperStatusResult.Updated)
        result as PaperStatusResult.Updated
        assertEquals("done", result.paper.status)
        assertEquals(listOf("p1" to "done"), api.statusUpdates)
    }

    @Test
    fun setStatusReportsRejection() = runTest {
        val api = FakePapersApi()
        api.rejectWith = 404

        val result = PapersRepository(api).setStatus("missing", "done")

        assertTrue(result is PaperStatusResult.Rejected)
        result as PaperStatusResult.Rejected
        assertEquals(404, result.code)
    }

    @Test
    fun downloadWritesPdfToTarget() = runTest {
        val api = FakePapersApi()
        api.pdfBytes = byteArrayOf(9, 8, 7, 6)
        val target = File.createTempFile("paper", ".pdf").also { it.delete() }

        val result = PapersRepository(api).download("p1", target)

        assertTrue(result is PaperDownloadResult.Ready)
        result as PaperDownloadResult.Ready
        assertEquals(listOf<Byte>(9, 8, 7, 6), result.file.readBytes().toList())
        target.delete()
    }
}

package com.graduateentrance.app

import com.graduateentrance.app.data.CaptureImage
import com.graduateentrance.app.data.CaptureRepository
import com.graduateentrance.app.data.CaptureResult
import com.graduateentrance.app.data.ExtractionOutcome
import com.graduateentrance.app.network.ChatConversationListDto
import com.graduateentrance.app.network.ChatHistoryDto
import com.graduateentrance.app.network.ChatSendResultDto
import com.graduateentrance.app.network.DueReviewsDto
import com.graduateentrance.app.network.ExtractedKnowledgePointDto
import com.graduateentrance.app.network.ExtractionResultDto
import com.graduateentrance.app.network.GraduateEntranceApi
import com.graduateentrance.app.network.PaperListDto
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
import com.graduateentrance.app.network.TodayDto
import com.graduateentrance.app.network.TodayTaskDto
import com.graduateentrance.app.network.VocabDictationDto
import com.graduateentrance.app.network.VocabGradeRequest
import com.graduateentrance.app.network.VocabGradeResultDto
import com.graduateentrance.app.network.VocabStatsDto
import com.graduateentrance.app.network.VocabTodayDto
import com.graduateentrance.app.network.VocabWordDto
import java.io.IOException
import kotlinx.coroutines.test.runTest
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import okhttp3.ResponseBody.Companion.toResponseBody
import okio.Buffer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response

private fun RequestBody.readText(): String {
    val buffer = Buffer()
    writeTo(buffer)
    return buffer.readUtf8()
}

private class FakeCaptureApi : GraduateEntranceApi {
    var offline = false
    var rejectWith: Int? = null
    var lastKind: String? = null
    var lastNote: String? = null
    var lastImageCount = 0

    override suspend fun ping(): ServiceStatus = ServiceStatus("ok", "test", "test")

    override suspend fun today(date: String): TodayDto = TodayDto(date, 0, 0, 0, emptyList())

    override suspend fun completeTask(taskId: String, payload: TaskCompletionRequest): TodayTaskDto =
        throw UnsupportedOperationException()

    override suspend fun dueReviews(includeDrafts: Boolean, limit: Int): DueReviewsDto =
        DueReviewsDto(0, "2026-08-05", emptyList())

    override suspend fun reviewProblem(problemId: String, payload: ReviewRequest): ReviewResultDto =
        throw UnsupportedOperationException()

    override suspend fun submitProblem(
        kind: RequestBody,
        note: RequestBody,
        images: List<MultipartBody.Part>,
    ): ProblemCreatedDto {
        if (offline) throw IOException("offline")
        rejectWith?.let { code ->
            throw HttpException(
                Response.error<ProblemCreatedDto>(
                    code,
                    "{}".toResponseBody("application/json".toMediaType()),
                ),
            )
        }
        lastKind = kind.readText()
        lastNote = note.readText()
        lastImageCount = images.size
        return ProblemCreatedDto("p1", "draft", List(images.size) { "img$it.jpg" })
    }

    override suspend fun extractProblem(problemId: String): ExtractionResultDto {
        if (offline) throw IOException("offline")
        rejectWith?.let { code ->
            throw HttpException(
                Response.error<ExtractionResultDto>(
                    code,
                    "{}".toResponseBody("application/json".toMediaType()),
                ),
            )
        }
        return ExtractionResultDto(
            problemId = problemId,
            model = "test-model",
            contentMd = "求极限",
            knowledgePoints = listOf(
                ExtractedKnowledgePointDto("kp1", "两个重要极限", "primary", 0.7),
            ),
            solution = null,
        )
    }

    override suspend fun papers(): PaperListDto = throw UnsupportedOperationException()

    override suspend fun papersToday(): PaperTodayDto = throw UnsupportedOperationException()

    override suspend fun setPaperStatus(
        paperId: String,
        payload: PaperStatusRequest,
    ): PaperStatusResultDto = throw UnsupportedOperationException()

    override suspend fun downloadPaper(paperId: String): ResponseBody =
        throw UnsupportedOperationException()

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

class CaptureRepositoryTest {
    private val images = listOf(
        CaptureImage(byteArrayOf(1, 2, 3), "image/jpeg"),
        CaptureImage(byteArrayOf(4, 5), "image/png"),
    )

    @Test
    fun submitProblemSendsKindNoteAndImages() = runTest {
        val api = FakeCaptureApi()
        val repository = CaptureRepository(api)

        val result = repository.submitProblem("hard", "第三章", images)

        assertTrue(result is CaptureResult.Created)
        result as CaptureResult.Created
        assertEquals("draft", result.problem.status)
        assertEquals(2, result.problem.images.size)
        assertEquals("hard", api.lastKind)
        assertEquals("第三章", api.lastNote)
        assertEquals(2, api.lastImageCount)
    }

    @Test
    fun submitProblemReportsOffline() = runTest {
        val api = FakeCaptureApi()
        api.offline = true

        assertTrue(
            CaptureRepository(api).submitProblem("wrong", "", images) is CaptureResult.Offline,
        )
    }

    @Test
    fun extractProblemReturnsResult() = runTest {
        val api = FakeCaptureApi()

        val outcome = CaptureRepository(api).extractProblem("p1")

        assertTrue(outcome is ExtractionOutcome.Extracted)
        outcome as ExtractionOutcome.Extracted
        assertEquals("求极限", outcome.result.contentMd)
        assertEquals("两个重要极限", outcome.result.knowledgePoints.single().knowledgePointName)
    }

    @Test
    fun extractProblemReportsRejection() = runTest {
        val api = FakeCaptureApi()
        api.rejectWith = 503

        val outcome = CaptureRepository(api).extractProblem("p1")

        assertTrue(outcome is ExtractionOutcome.Rejected)
        outcome as ExtractionOutcome.Rejected
        assertEquals(503, outcome.code)
    }

    @Test
    fun submitProblemReportsRejection() = runTest {
        val api = FakeCaptureApi()
        api.rejectWith = 400

        val result = CaptureRepository(api).submitProblem("wrong", "", images)

        assertTrue(result is CaptureResult.Rejected)
        result as CaptureResult.Rejected
        assertEquals(400, result.code)
    }
}

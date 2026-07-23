package com.graduateentrance.app

import com.graduateentrance.app.data.GradeResult
import com.graduateentrance.app.data.ReviewsLoadResult
import com.graduateentrance.app.data.ReviewsRepository
import com.graduateentrance.app.network.ChatConversationListDto
import com.graduateentrance.app.network.ChatHistoryDto
import com.graduateentrance.app.network.ChatSendResultDto
import com.graduateentrance.app.network.DueReviewsDto
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
import com.graduateentrance.app.network.ReviewProblemDto
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

private fun reviewProblem(id: String, status: String = "confirmed") = ReviewProblemDto(
    id = id,
    subjectName = "数学一",
    contentMd = "求极限",
    kind = "wrong",
    status = status,
    dueDate = "2026-08-05",
    reps = 1,
    knowledgePoints = emptyList(),
    solutions = emptyList(),
)

private class FakeReviewsApi : GraduateEntranceApi {
    var offline = false
    var rejectWith: Int? = null
    var dueResponse = DueReviewsDto(0, "2026-08-05", emptyList())
    val graded = mutableListOf<Pair<String, String>>()
    var lastIncludeDrafts: Boolean? = null

    override suspend fun ping(): ServiceStatus = ServiceStatus("ok", "test", "test")

    override suspend fun today(date: String): TodayDto = TodayDto(date, 0, 0, 0, emptyList())

    override suspend fun completeTask(taskId: String, payload: TaskCompletionRequest): TodayTaskDto =
        throw UnsupportedOperationException()

    override suspend fun updateTask(taskId: String, payload: TaskUpdateRequest): TodayTaskDto =
        throw UnsupportedOperationException()

    override suspend fun dueReviews(includeDrafts: Boolean, limit: Int): DueReviewsDto {
        if (offline) throw IOException("offline")
        lastIncludeDrafts = includeDrafts
        return dueResponse
    }

    override suspend fun reviewProblem(problemId: String, payload: ReviewRequest): ReviewResultDto {
        if (offline) throw IOException("offline")
        rejectWith?.let { code ->
            throw HttpException(
                Response.error<ReviewResultDto>(
                    code,
                    "{}".toResponseBody("application/json".toMediaType()),
                ),
            )
        }
        graded.add(problemId to payload.grade)
        return ReviewResultDto(payload.grade, 2.6, 6, 2, "2026-08-11")
    }

    override suspend fun submitProblem(
        kind: RequestBody,
        note: RequestBody,
        images: List<MultipartBody.Part>,
    ): ProblemCreatedDto = ProblemCreatedDto("p", "draft", emptyList())

    override suspend fun extractProblem(problemId: String): ExtractionResultDto =
        ExtractionResultDto(problemId, "test", "", emptyList(), null)

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

class ReviewsRepositoryTest {
    @Test
    fun loadDueReviewsReturnsProblems() = runTest {
        val api = FakeReviewsApi()
        api.dueResponse = DueReviewsDto(
            2,
            "2026-08-05",
            listOf(reviewProblem("p1"), reviewProblem("p2", status = "draft")),
        )
        val repository = ReviewsRepository(api)

        val result = repository.loadDueReviews(includeDrafts = false)

        assertTrue(result is ReviewsLoadResult.Loaded)
        result as ReviewsLoadResult.Loaded
        assertEquals(2, result.total)
        assertEquals(listOf("p1", "p2"), result.problems.map { it.id })
        assertEquals(false, api.lastIncludeDrafts)
    }

    @Test
    fun loadDueReviewsReportsOffline() = runTest {
        val api = FakeReviewsApi()
        api.offline = true

        assertTrue(ReviewsRepository(api).loadDueReviews(true) is ReviewsLoadResult.Offline)
    }

    @Test
    fun gradeSubmitsAndReturnsSchedule() = runTest {
        val api = FakeReviewsApi()
        val repository = ReviewsRepository(api)

        val result = repository.grade("p1", "mastered")

        assertTrue(result is GradeResult.Graded)
        result as GradeResult.Graded
        assertEquals("2026-08-11", result.result.dueDate)
        assertEquals(6, result.result.intervalDays)
        assertEquals(listOf("p1" to "mastered"), api.graded)
    }

    @Test
    fun gradeReportsRejection() = runTest {
        val api = FakeReviewsApi()
        api.rejectWith = 404

        val result = ReviewsRepository(api).grade("missing", "forgot")

        assertTrue(result is GradeResult.Rejected)
        result as GradeResult.Rejected
        assertEquals(404, result.code)
    }
}

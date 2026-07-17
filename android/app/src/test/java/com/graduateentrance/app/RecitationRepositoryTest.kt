package com.graduateentrance.app

import com.graduateentrance.app.data.RecitationLoadResult
import com.graduateentrance.app.data.RecitationRepository
import com.graduateentrance.app.data.ReciteActionResult
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
import com.graduateentrance.app.network.RecitationGroupDto
import com.graduateentrance.app.network.RecitationItemDto
import com.graduateentrance.app.network.RecitationListDto
import com.graduateentrance.app.network.RecitationStatsDto
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
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response

private fun item(id: String, recitedToday: Boolean = false) = RecitationItemDto(
    id = id,
    subject = "politics",
    category = "马原",
    title = "条目 $id",
    contentMd = "内容 $id",
    reciteCount = 1,
    lastRecitedOn = null,
    recitedToday = recitedToday,
)

private val emptyStats = RecitationStatsDto(0, 0, 0)

private class FakeRecitationApi : GraduateEntranceApi {
    var offline = false
    var rejectWith: Int? = null
    var listResponse = RecitationListDto(emptyList(), emptyStats)
    var todayResponse = RecitationTodayDto("2026-07-17", null, emptyStats)
    val reciteCalls = mutableListOf<Pair<String, Boolean>>()

    override suspend fun ping(): ServiceStatus = ServiceStatus("ok", "test", "test")

    override suspend fun today(date: String): TodayDto = TodayDto(date, 0, 0, 0, emptyList())

    override suspend fun completeTask(taskId: String, payload: TaskCompletionRequest): TodayTaskDto =
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

    override suspend fun papers(): PaperListDto = throw UnsupportedOperationException()

    override suspend fun papersToday(): PaperTodayDto = throw UnsupportedOperationException()

    override suspend fun setPaperStatus(
        paperId: String,
        payload: PaperStatusRequest,
    ): PaperStatusResultDto = throw UnsupportedOperationException()

    override suspend fun downloadPaper(paperId: String): ResponseBody =
        throw UnsupportedOperationException()

    private fun maybeFail() {
        if (offline) throw IOException("offline")
        rejectWith?.let { code ->
            throw HttpException(
                Response.error<RecitationListDto>(
                    code,
                    "{}".toResponseBody("application/json".toMediaType()),
                ),
            )
        }
    }

    override suspend fun recitations(subject: String?): RecitationListDto {
        maybeFail()
        return listResponse
    }

    override suspend fun recitationToday(subject: String?): RecitationTodayDto {
        maybeFail()
        return todayResponse
    }

    override suspend fun reciteItem(itemId: String, payload: ReciteRequest): ReciteResultDto {
        maybeFail()
        reciteCalls.add(itemId to payload.undo)
        return ReciteResultDto(item(itemId, recitedToday = !payload.undo))
    }

    override suspend fun vocabToday(): VocabTodayDto = throw UnsupportedOperationException()

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

class RecitationRepositoryTest {
    @Test
    fun loadReturnsTodayGroupsAndStats() = runTest {
        val api = FakeRecitationApi()
        val stats = RecitationStatsDto(2, 1, 0)
        api.todayResponse = RecitationTodayDto("2026-07-17", item("r1"), stats)
        api.listResponse = RecitationListDto(
            listOf(RecitationGroupDto("马原", listOf(item("r1"), item("r2")))),
            stats,
        )
        val repository = RecitationRepository(api)

        val result = repository.load("politics")

        assertTrue(result is RecitationLoadResult.Loaded)
        result as RecitationLoadResult.Loaded
        assertEquals("r1", result.today?.id)
        assertEquals(listOf("马原"), result.groups.map { it.category })
        assertEquals(2, result.stats.totalCount)
    }

    @Test
    fun loadReturnsOfflineOnIoError() = runTest {
        val api = FakeRecitationApi()
        api.offline = true

        val result = RecitationRepository(api).load("politics")

        assertTrue(result is RecitationLoadResult.Offline)
    }

    @Test
    fun loadReturnsRejectedOnHttpError() = runTest {
        val api = FakeRecitationApi()
        api.rejectWith = 401

        val result = RecitationRepository(api).load("politics")

        assertTrue(result is RecitationLoadResult.Rejected)
        assertEquals(401, (result as RecitationLoadResult.Rejected).code)
    }

    @Test
    fun reciteSendsUndoFlag() = runTest {
        val api = FakeRecitationApi()
        val repository = RecitationRepository(api)

        val done = repository.recite("r1", undo = false)
        val undone = repository.recite("r1", undo = true)

        assertTrue(done is ReciteActionResult.Updated)
        assertTrue((done as ReciteActionResult.Updated).item.recitedToday)
        assertTrue(undone is ReciteActionResult.Updated)
        assertEquals(listOf("r1" to false, "r1" to true), api.reciteCalls)
    }

    @Test
    fun reciteReturnsOfflineOnIoError() = runTest {
        val api = FakeRecitationApi()
        api.offline = true

        val result = RecitationRepository(api).recite("r1", undo = false)

        assertTrue(result is ReciteActionResult.Offline)
    }
}

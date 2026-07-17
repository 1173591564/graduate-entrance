package com.graduateentrance.app

import com.graduateentrance.app.data.VocabGradeActionResult
import com.graduateentrance.app.data.VocabLoadResult
import com.graduateentrance.app.data.VocabRepository
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
import com.graduateentrance.app.network.ReviewRequest
import com.graduateentrance.app.network.ReviewResultDto
import com.graduateentrance.app.network.ServiceStatus
import com.graduateentrance.app.network.TaskCompletionRequest
import com.graduateentrance.app.network.TodayDto
import com.graduateentrance.app.network.TodayTaskDto
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

private fun word(id: String, dueDate: String? = null, reps: Int = 0) = VocabWordDto(
    id = id,
    word = "word-$id",
    meaning = "释义 $id",
    bookPage = 1,
    ef = 2.5,
    intervalDays = 1,
    dueDate = dueDate,
    reps = reps,
)

private class FakeVocabApi : GraduateEntranceApi {
    var offline = false
    var rejectWith: Int? = null
    var todayResponse = VocabTodayDto("2026-07-17", emptyList(), emptyList(), 0, 0, 0)
    val gradeCalls = mutableListOf<Pair<String, String>>()

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

    override suspend fun recitations(subject: String?): RecitationListDto =
        throw UnsupportedOperationException()

    override suspend fun recitationToday(subject: String?): RecitationTodayDto =
        throw UnsupportedOperationException()

    override suspend fun reciteItem(itemId: String, payload: ReciteRequest): ReciteResultDto =
        throw UnsupportedOperationException()

    private fun maybeFail() {
        if (offline) throw IOException("offline")
        rejectWith?.let { code ->
            throw HttpException(
                Response.error<VocabTodayDto>(
                    code,
                    "{}".toResponseBody("application/json".toMediaType()),
                ),
            )
        }
    }

    override suspend fun vocabToday(): VocabTodayDto {
        maybeFail()
        return todayResponse
    }

    override suspend fun gradeVocabWord(
        wordId: String,
        payload: VocabGradeRequest,
    ): VocabGradeResultDto {
        maybeFail()
        gradeCalls.add(wordId to payload.grade)
        return VocabGradeResultDto(
            word = word(wordId, dueDate = "2026-07-20", reps = 1),
            grade = payload.grade,
            dueDate = "2026-07-20",
        )
    }

    override suspend fun vocabStats(): VocabStatsDto = throw UnsupportedOperationException()
}

class VocabRepositoryTest {
    @Test
    fun loadReturnsTodayQueue() = runTest {
        val api = FakeVocabApi()
        api.todayResponse = VocabTodayDto(
            date = "2026-07-17",
            dueWords = listOf(word("d1", dueDate = "2026-07-17", reps = 2)),
            newWords = listOf(word("n1"), word("n2")),
            dueCount = 1,
            learnedCount = 5,
            totalCount = 100,
        )

        val result = VocabRepository(api).load()

        assertTrue(result is VocabLoadResult.Loaded)
        result as VocabLoadResult.Loaded
        assertEquals(1, result.today.dueWords.size)
        assertEquals(2, result.today.newWords.size)
        assertEquals(100, result.today.totalCount)
    }

    @Test
    fun loadReturnsOfflineOnIoError() = runTest {
        val api = FakeVocabApi()
        api.offline = true

        assertTrue(VocabRepository(api).load() is VocabLoadResult.Offline)
    }

    @Test
    fun loadReturnsRejectedOnHttpError() = runTest {
        val api = FakeVocabApi()
        api.rejectWith = 401

        val result = VocabRepository(api).load()

        assertTrue(result is VocabLoadResult.Rejected)
        assertEquals(401, (result as VocabLoadResult.Rejected).code)
    }

    @Test
    fun gradeSendsGradeAndReturnsResult() = runTest {
        val api = FakeVocabApi()

        val result = VocabRepository(api).grade("w1", "mastered")

        assertTrue(result is VocabGradeActionResult.Graded)
        assertEquals("mastered", (result as VocabGradeActionResult.Graded).result.grade)
        assertEquals(listOf("w1" to "mastered"), api.gradeCalls)
    }

    @Test
    fun gradeReturnsOfflineOnIoError() = runTest {
        val api = FakeVocabApi()
        api.offline = true

        assertTrue(VocabRepository(api).grade("w1", "forgot") is VocabGradeActionResult.Offline)
    }
}

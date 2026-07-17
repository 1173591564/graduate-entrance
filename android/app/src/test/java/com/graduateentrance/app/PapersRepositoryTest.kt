package com.graduateentrance.app

import com.graduateentrance.app.data.PaperDownloadResult
import com.graduateentrance.app.data.PaperStatusResult
import com.graduateentrance.app.data.PapersLoadResult
import com.graduateentrance.app.data.PapersRepository
import com.graduateentrance.app.network.DueReviewsDto
import com.graduateentrance.app.network.ExtractionResultDto
import com.graduateentrance.app.network.GraduateEntranceApi
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
import com.graduateentrance.app.network.TodayDto
import com.graduateentrance.app.network.TodayTaskDto
import com.graduateentrance.app.network.VocabGradeRequest
import com.graduateentrance.app.network.VocabGradeResultDto
import com.graduateentrance.app.network.VocabStatsDto
import com.graduateentrance.app.network.VocabTodayDto
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

    override suspend fun vocabToday(): VocabTodayDto = throw UnsupportedOperationException()

    override suspend fun gradeVocabWord(
        wordId: String,
        payload: VocabGradeRequest,
    ): VocabGradeResultDto = throw UnsupportedOperationException()

    override suspend fun vocabStats(): VocabStatsDto = throw UnsupportedOperationException()
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

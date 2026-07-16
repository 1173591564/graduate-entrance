package com.graduateentrance.app

import com.graduateentrance.app.data.CaptureImage
import com.graduateentrance.app.data.CaptureRepository
import com.graduateentrance.app.data.CaptureResult
import com.graduateentrance.app.network.DueReviewsDto
import com.graduateentrance.app.network.GraduateEntranceApi
import com.graduateentrance.app.network.ProblemCreatedDto
import com.graduateentrance.app.network.ReviewRequest
import com.graduateentrance.app.network.ReviewResultDto
import com.graduateentrance.app.network.ServiceStatus
import com.graduateentrance.app.network.TaskCompletionRequest
import com.graduateentrance.app.network.TodayDto
import com.graduateentrance.app.network.TodayTaskDto
import java.io.IOException
import kotlinx.coroutines.test.runTest
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
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
    fun submitProblemReportsRejection() = runTest {
        val api = FakeCaptureApi()
        api.rejectWith = 400

        val result = CaptureRepository(api).submitProblem("wrong", "", images)

        assertTrue(result is CaptureResult.Rejected)
        result as CaptureResult.Rejected
        assertEquals(400, result.code)
    }
}

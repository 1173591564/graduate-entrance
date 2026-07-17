package com.graduateentrance.app

import com.graduateentrance.app.data.CaptureImage
import com.graduateentrance.app.data.ChatConversationsResult
import com.graduateentrance.app.data.ChatDeleteResult
import com.graduateentrance.app.data.ChatRepository
import com.graduateentrance.app.data.ChatSendResult
import com.graduateentrance.app.network.ChatConversationDto
import com.graduateentrance.app.network.ChatConversationListDto
import com.graduateentrance.app.network.ChatHistoryDto
import com.graduateentrance.app.network.ChatMessageDto
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

private fun conversation(id: String) = ChatConversationDto(
    id = id,
    title = "对话 $id",
    createdAt = "2026-07-17T10:00:00Z",
    updatedAt = "2026-07-17T10:00:00Z",
)

private fun message(id: String, conversationId: String, role: String) = ChatMessageDto(
    id = id,
    conversationId = conversationId,
    role = role,
    contentMd = "内容 $id",
    images = emptyList(),
    createdAt = "2026-07-17T10:00:00Z",
)

private class FakeChatApi : GraduateEntranceApi {
    var offline = false
    var rejectWith: Int? = null
    val sendCalls = mutableListOf<Pair<String?, Int>>()
    val deletedIds = mutableListOf<String>()

    override suspend fun ping(): ServiceStatus = ServiceStatus("ok", "test", "test")

    override suspend fun today(date: String): TodayDto = TodayDto(date, 0, 0, 0, emptyList())

    override suspend fun completeTask(taskId: String, payload: TaskCompletionRequest): TodayTaskDto =
        throw UnsupportedOperationException()

    override suspend fun dueReviews(includeDrafts: Boolean, limit: Int): DueReviewsDto =
        throw UnsupportedOperationException()

    override suspend fun reviewProblem(problemId: String, payload: ReviewRequest): ReviewResultDto =
        throw UnsupportedOperationException()

    override suspend fun submitProblem(
        kind: RequestBody,
        note: RequestBody,
        images: List<MultipartBody.Part>,
    ): ProblemCreatedDto = throw UnsupportedOperationException()

    override suspend fun extractProblem(problemId: String): ExtractionResultDto =
        throw UnsupportedOperationException()

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

    override suspend fun vocabToday(): VocabTodayDto = throw UnsupportedOperationException()

    override suspend fun gradeVocabWord(
        wordId: String,
        payload: VocabGradeRequest,
    ): VocabGradeResultDto = throw UnsupportedOperationException()

    override suspend fun vocabDictation(): VocabDictationDto = throw UnsupportedOperationException()

    override suspend fun enrichVocabWord(wordId: String): VocabWordDto =
        throw UnsupportedOperationException()

    override suspend fun vocabStats(): VocabStatsDto = throw UnsupportedOperationException()

    private fun maybeFail() {
        if (offline) throw IOException("offline")
        rejectWith?.let { code ->
            throw HttpException(
                Response.error<ChatSendResultDto>(
                    code,
                    "{}".toResponseBody("application/json".toMediaType()),
                ),
            )
        }
    }

    override suspend fun chatConversations(): ChatConversationListDto {
        maybeFail()
        return ChatConversationListDto(2, listOf(conversation("c1"), conversation("c2")))
    }

    override suspend fun chatHistory(conversationId: String): ChatHistoryDto {
        maybeFail()
        return ChatHistoryDto(
            conversation = conversation(conversationId),
            messages = listOf(
                message("m1", conversationId, "user"),
                message("m2", conversationId, "assistant"),
            ),
        )
    }

    override suspend fun deleteChatConversation(conversationId: String): Response<Unit> {
        maybeFail()
        deletedIds.add(conversationId)
        return Response.success(Unit)
    }

    override suspend fun sendChatMessage(
        conversationId: RequestBody?,
        content: RequestBody,
        images: List<MultipartBody.Part>,
    ): ChatSendResultDto {
        maybeFail()
        sendCalls.add((if (conversationId == null) null else "set") to images.size)
        return ChatSendResultDto(
            conversation = conversation("c1"),
            userMessage = message("m1", "c1", "user"),
            reply = message("m2", "c1", "assistant"),
            model = "test-model",
        )
    }
}

class ChatRepositoryTest {
    @Test
    fun `send returns reply and passes image parts`() = runTest {
        val api = FakeChatApi()
        val repository = ChatRepository(api)

        val result = repository.send(
            conversationId = null,
            content = "极限怎么求？",
            images = listOf(CaptureImage(byteArrayOf(1, 2, 3), "image/jpeg")),
        )

        assertTrue(result is ChatSendResult.Sent)
        val sent = result as ChatSendResult.Sent
        assertEquals("test-model", sent.result.model)
        assertEquals("assistant", sent.result.reply.role)
        assertEquals(listOf(null as String? to 1), api.sendCalls)
    }

    @Test
    fun `send maps io failure to offline`() = runTest {
        val api = FakeChatApi().apply { offline = true }
        val repository = ChatRepository(api)

        val result = repository.send(null, "问题", emptyList())

        assertTrue(result is ChatSendResult.Offline)
    }

    @Test
    fun `send maps http failure to rejected`() = runTest {
        val api = FakeChatApi().apply { rejectWith = 503 }
        val repository = ChatRepository(api)

        val result = repository.send(null, "问题", emptyList())

        assertTrue(result is ChatSendResult.Rejected)
        assertEquals(503, (result as ChatSendResult.Rejected).code)
    }

    @Test
    fun `conversations loads list`() = runTest {
        val repository = ChatRepository(FakeChatApi())

        val result = repository.conversations()

        assertTrue(result is ChatConversationsResult.Loaded)
        assertEquals(2, (result as ChatConversationsResult.Loaded).list.conversations.size)
    }

    @Test
    fun `delete reports success`() = runTest {
        val api = FakeChatApi()
        val repository = ChatRepository(api)

        val result = repository.delete("c1")

        assertTrue(result is ChatDeleteResult.Deleted)
        assertEquals(listOf("c1"), api.deletedIds)
    }
}

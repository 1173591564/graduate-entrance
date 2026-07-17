package com.graduateentrance.app.data

import com.graduateentrance.app.network.ChatConversationListDto
import com.graduateentrance.app.network.ChatHistoryDto
import com.graduateentrance.app.network.ChatSendResultDto
import com.graduateentrance.app.network.GraduateEntranceApi
import java.io.IOException
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.HttpException

sealed interface ChatConversationsResult {
    data class Loaded(val list: ChatConversationListDto) : ChatConversationsResult
    data object Offline : ChatConversationsResult
    data class Rejected(val code: Int) : ChatConversationsResult
}

sealed interface ChatHistoryResult {
    data class Loaded(val history: ChatHistoryDto) : ChatHistoryResult
    data object Offline : ChatHistoryResult
    data class Rejected(val code: Int) : ChatHistoryResult
}

sealed interface ChatSendResult {
    data class Sent(val result: ChatSendResultDto) : ChatSendResult
    data object Offline : ChatSendResult
    data class Rejected(val code: Int) : ChatSendResult
}

sealed interface ChatDeleteResult {
    data object Deleted : ChatDeleteResult
    data object Offline : ChatDeleteResult
    data class Rejected(val code: Int) : ChatDeleteResult
}

private val CHAT_IMAGE_EXTENSIONS = mapOf(
    "image/jpeg" to "jpg",
    "image/png" to "png",
    "image/webp" to "webp",
)

class ChatRepository(private val api: GraduateEntranceApi) {
    suspend fun conversations(): ChatConversationsResult =
        try {
            ChatConversationsResult.Loaded(api.chatConversations())
        } catch (_: IOException) {
            ChatConversationsResult.Offline
        } catch (error: HttpException) {
            ChatConversationsResult.Rejected(error.code())
        }

    suspend fun history(conversationId: String): ChatHistoryResult =
        try {
            ChatHistoryResult.Loaded(api.chatHistory(conversationId))
        } catch (_: IOException) {
            ChatHistoryResult.Offline
        } catch (error: HttpException) {
            ChatHistoryResult.Rejected(error.code())
        }

    suspend fun send(
        conversationId: String?,
        content: String,
        images: List<CaptureImage>,
    ): ChatSendResult =
        try {
            val parts = images.mapIndexed { index, image ->
                val extension = CHAT_IMAGE_EXTENSIONS[image.mimeType] ?: "jpg"
                MultipartBody.Part.createFormData(
                    "images",
                    "chat-$index.$extension",
                    image.bytes.toRequestBody(image.mimeType.toMediaType()),
                )
            }
            val result = api.sendChatMessage(
                conversationId = conversationId?.toRequestBody("text/plain".toMediaType()),
                content = content.toRequestBody("text/plain".toMediaType()),
                images = parts,
            )
            ChatSendResult.Sent(result)
        } catch (_: IOException) {
            ChatSendResult.Offline
        } catch (error: HttpException) {
            ChatSendResult.Rejected(error.code())
        }

    suspend fun delete(conversationId: String): ChatDeleteResult =
        try {
            val response = api.deleteChatConversation(conversationId)
            if (response.isSuccessful) {
                ChatDeleteResult.Deleted
            } else {
                ChatDeleteResult.Rejected(response.code())
            }
        } catch (_: IOException) {
            ChatDeleteResult.Offline
        } catch (error: HttpException) {
            ChatDeleteResult.Rejected(error.code())
        }
}

package com.graduateentrance.app.ui

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.graduateentrance.app.data.CaptureImage
import com.graduateentrance.app.data.ChatConversationsResult
import com.graduateentrance.app.data.ChatDeleteResult
import com.graduateentrance.app.data.ChatHistoryResult
import com.graduateentrance.app.data.ChatRepository
import com.graduateentrance.app.data.ChatSendResult
import com.graduateentrance.app.network.ChatConversationDto
import com.graduateentrance.app.network.ChatMessageDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

const val MAX_CHAT_IMAGES = 4

data class ChatUiState(
    val conversations: List<ChatConversationDto> = emptyList(),
    val conversationId: String? = null,
    val conversationTitle: String = "",
    val messages: List<ChatMessageDto> = emptyList(),
    val input: String = "",
    val pendingImages: List<Uri> = emptyList(),
    val sending: Boolean = false,
    val loading: Boolean = false,
    val notice: String? = null,
)

class ChatViewModel(
    private val repository: ChatRepository,
    private val readImage: suspend (Uri) -> CaptureImage?,
) : ViewModel() {
    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    fun setInput(value: String) {
        _uiState.update { it.copy(input = value) }
    }

    fun prefillInput(value: String) {
        if (value.isNotBlank()) {
            _uiState.update { it.copy(input = value) }
        }
    }

    fun addImages(uris: List<Uri>) {
        _uiState.update { state ->
            val merged = (state.pendingImages + uris).distinct().take(MAX_CHAT_IMAGES)
            state.copy(pendingImages = merged)
        }
    }

    fun removeImage(uri: Uri) {
        _uiState.update { state ->
            state.copy(pendingImages = state.pendingImages.filterNot { it == uri })
        }
    }

    fun dismissNotice() {
        _uiState.update { it.copy(notice = null) }
    }

    fun refreshConversations() {
        viewModelScope.launch {
            when (val result = repository.conversations()) {
                is ChatConversationsResult.Loaded -> _uiState.update {
                    it.copy(conversations = result.list.conversations)
                }
                ChatConversationsResult.Offline -> _uiState.update {
                    it.copy(notice = "网络不可用，历史对话加载失败")
                }
                is ChatConversationsResult.Rejected -> _uiState.update {
                    it.copy(notice = "历史对话加载失败（HTTP ${result.code}）")
                }
            }
        }
    }

    fun startNewConversation() {
        _uiState.update {
            it.copy(
                conversationId = null,
                conversationTitle = "",
                messages = emptyList(),
                pendingImages = emptyList(),
            )
        }
    }

    fun openConversation(conversationId: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true) }
            when (val result = repository.history(conversationId)) {
                is ChatHistoryResult.Loaded -> _uiState.update {
                    it.copy(
                        loading = false,
                        conversationId = result.history.conversation.id,
                        conversationTitle = result.history.conversation.title,
                        messages = result.history.messages,
                        pendingImages = emptyList(),
                    )
                }
                ChatHistoryResult.Offline -> _uiState.update {
                    it.copy(loading = false, notice = "网络不可用，对话加载失败")
                }
                is ChatHistoryResult.Rejected -> _uiState.update {
                    it.copy(loading = false, notice = "对话加载失败（HTTP ${result.code}）")
                }
            }
        }
    }

    fun deleteConversation(conversationId: String) {
        viewModelScope.launch {
            when (val result = repository.delete(conversationId)) {
                ChatDeleteResult.Deleted -> {
                    _uiState.update { state ->
                        val cleared = state.conversationId == conversationId
                        state.copy(
                            conversations = state.conversations.filterNot {
                                it.id == conversationId
                            },
                            conversationId = if (cleared) null else state.conversationId,
                            conversationTitle = if (cleared) "" else state.conversationTitle,
                            messages = if (cleared) emptyList() else state.messages,
                        )
                    }
                }
                ChatDeleteResult.Offline -> _uiState.update {
                    it.copy(notice = "网络不可用，删除失败")
                }
                is ChatDeleteResult.Rejected -> _uiState.update {
                    it.copy(notice = "删除失败（HTTP ${result.code}）")
                }
            }
        }
    }

    fun send() {
        val state = _uiState.value
        if (state.sending || (state.input.isBlank() && state.pendingImages.isEmpty())) {
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(sending = true, notice = null) }
            val images = state.pendingImages.mapNotNull { readImage(it) }
            if (state.pendingImages.isNotEmpty() && images.isEmpty()) {
                _uiState.update { it.copy(sending = false, notice = "读取图片失败，请重新选择") }
                return@launch
            }
            val result = repository.send(state.conversationId, state.input.trim(), images)
            when (result) {
                is ChatSendResult.Sent -> {
                    val sent = result.result
                    _uiState.update {
                        it.copy(
                            sending = false,
                            conversationId = sent.conversation.id,
                            conversationTitle = sent.conversation.title,
                            messages = it.messages + sent.userMessage + sent.reply,
                            input = "",
                            pendingImages = emptyList(),
                        )
                    }
                    refreshConversations()
                }
                ChatSendResult.Offline -> _uiState.update {
                    it.copy(sending = false, notice = "网络不可用，发送失败")
                }
                is ChatSendResult.Rejected -> {
                    val hint = if (result.code == 503) {
                        "服务器未配置 AI 接口（HTTP 503）"
                    } else {
                        "发送失败（HTTP ${result.code}）"
                    }
                    _uiState.update { it.copy(sending = false, notice = hint) }
                }
            }
        }
    }

    class Factory(
        private val repository: ChatRepository,
        private val readImage: suspend (Uri) -> CaptureImage?,
    ) : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            require(modelClass.isAssignableFrom(ChatViewModel::class.java)) {
                "Unknown ViewModel class: ${modelClass.name}"
            }
            @Suppress("UNCHECKED_CAST")
            return ChatViewModel(repository, readImage) as T
        }
    }
}

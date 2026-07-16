package com.graduateentrance.app.ui

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.graduateentrance.app.data.CaptureImage
import com.graduateentrance.app.data.CaptureRepository
import com.graduateentrance.app.data.CaptureResult
import com.graduateentrance.app.data.ExtractionOutcome
import com.graduateentrance.app.network.ExtractionResultDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class CaptureUiState(
    val kind: String = "wrong",
    val note: String = "",
    val imageUris: List<Uri> = emptyList(),
    val submitting: Boolean = false,
    val extracting: Boolean = false,
    val extraction: ExtractionResultDto? = null,
    val notice: String? = null,
)

const val MAX_CAPTURE_IMAGES = 6

class CaptureViewModel(
    private val repository: CaptureRepository,
    private val readImage: suspend (Uri) -> CaptureImage?,
) : ViewModel() {
    private val _uiState = MutableStateFlow(CaptureUiState())
    val uiState: StateFlow<CaptureUiState> = _uiState.asStateFlow()

    fun setKind(kind: String) {
        _uiState.update { it.copy(kind = kind) }
    }

    fun setNote(note: String) {
        _uiState.update { it.copy(note = note) }
    }

    fun dismissExtraction() {
        _uiState.update { it.copy(extraction = null) }
    }

    fun addImages(uris: List<Uri>) {
        _uiState.update { state ->
            val merged = (state.imageUris + uris).distinct().take(MAX_CAPTURE_IMAGES)
            state.copy(imageUris = merged)
        }
    }

    fun removeImage(uri: Uri) {
        _uiState.update { state ->
            state.copy(imageUris = state.imageUris.filterNot { it == uri })
        }
    }

    fun submit() {
        val state = _uiState.value
        if (state.imageUris.isEmpty() || state.submitting) {
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(submitting = true, notice = null) }
            val images = state.imageUris.mapNotNull { readImage(it) }
            if (images.isEmpty()) {
                _uiState.update { it.copy(submitting = false, notice = "读取图片失败，请重新选择") }
                return@launch
            }
            when (val result = repository.submitProblem(state.kind, state.note, images)) {
                is CaptureResult.Created -> {
                    _uiState.update {
                        CaptureUiState(
                            kind = it.kind,
                            extracting = true,
                            notice = "已上传为草稿（${result.problem.images.size} 张图），AI 识别中…",
                        )
                    }
                    extract(result.problem.id)
                }
                CaptureResult.Offline -> _uiState.update {
                    it.copy(submitting = false, notice = "网络不可用，上传失败")
                }
                is CaptureResult.Rejected -> _uiState.update {
                    it.copy(submitting = false, notice = "上传失败（HTTP ${result.code}）")
                }
            }
        }
    }

    private fun extract(problemId: String) {
        viewModelScope.launch {
            val notice = when (val outcome = repository.extractProblem(problemId)) {
                is ExtractionOutcome.Extracted -> {
                    _uiState.update { it.copy(extraction = outcome.result) }
                    "AI 识别完成，请到 Web 审核台确认定稿"
                }
                ExtractionOutcome.Offline -> "草稿已上传，但 AI 识别网络失败，可在 Web 审核台重试"
                is ExtractionOutcome.Rejected ->
                    "草稿已上传，但 AI 识别失败（HTTP ${outcome.code}），可在 Web 审核台重试"
            }
            _uiState.update { it.copy(extracting = false, notice = notice) }
        }
    }

    class Factory(
        private val repository: CaptureRepository,
        private val readImage: suspend (Uri) -> CaptureImage?,
    ) : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            require(modelClass.isAssignableFrom(CaptureViewModel::class.java)) {
                "Unknown ViewModel class: ${modelClass.name}"
            }
            @Suppress("UNCHECKED_CAST")
            return CaptureViewModel(repository, readImage) as T
        }
    }
}

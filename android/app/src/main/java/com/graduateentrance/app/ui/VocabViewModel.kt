package com.graduateentrance.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.graduateentrance.app.data.VocabGradeActionResult
import com.graduateentrance.app.data.VocabLoadResult
import com.graduateentrance.app.data.VocabRepository
import com.graduateentrance.app.network.VocabWordDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class VocabUiState(
    val loading: Boolean = true,
    val queue: List<VocabWordDto> = emptyList(),
    val revealed: Boolean = false,
    val gradedCount: Int = 0,
    val sessionTotal: Int = 0,
    val learnedCount: Int = 0,
    val totalCount: Int = 0,
    val dueCount: Int = 0,
    val grading: Boolean = false,
    val notice: String? = null,
    val error: String? = null,
) {
    val current: VocabWordDto? get() = queue.firstOrNull()
}

class VocabViewModel(private val repository: VocabRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(VocabUiState())
    val uiState: StateFlow<VocabUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, error = null) }
            when (val result = repository.load()) {
                is VocabLoadResult.Loaded -> {
                    val queue = result.today.dueWords + result.today.newWords
                    _uiState.update {
                        it.copy(
                            loading = false,
                            queue = queue,
                            revealed = false,
                            gradedCount = 0,
                            sessionTotal = queue.size,
                            learnedCount = result.today.learnedCount,
                            totalCount = result.today.totalCount,
                            dueCount = result.today.dueCount,
                        )
                    }
                }
                VocabLoadResult.Offline -> _uiState.update {
                    it.copy(loading = false, error = "网络不可用，请稍后重试")
                }
                is VocabLoadResult.Rejected -> _uiState.update {
                    it.copy(loading = false, error = "加载失败（HTTP ${result.code}）")
                }
            }
        }
    }

    fun reveal() {
        _uiState.update { it.copy(revealed = true) }
    }

    fun grade(wordId: String, grade: String) {
        if (_uiState.value.grading) return
        viewModelScope.launch {
            _uiState.update { it.copy(grading = true, notice = null) }
            when (val result = repository.grade(wordId, grade)) {
                is VocabGradeActionResult.Graded -> _uiState.update { state ->
                    state.copy(
                        grading = false,
                        queue = state.queue.filterNot { it.id == wordId },
                        revealed = false,
                        gradedCount = state.gradedCount + 1,
                        learnedCount = if (result.result.word.reps == 1) {
                            state.learnedCount + 1
                        } else {
                            state.learnedCount
                        },
                        notice = "已评级，下次复习 ${result.result.dueDate}",
                    )
                }
                VocabGradeActionResult.Offline -> _uiState.update {
                    it.copy(grading = false, notice = "网络不可用，评级未提交")
                }
                is VocabGradeActionResult.Rejected -> _uiState.update {
                    it.copy(grading = false, notice = "评级失败（HTTP ${result.code}）")
                }
            }
        }
    }

    fun consumeNotice() {
        _uiState.update { it.copy(notice = null) }
    }

    class Factory(private val repository: VocabRepository) : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            require(modelClass.isAssignableFrom(VocabViewModel::class.java)) {
                "Unknown ViewModel class: ${modelClass.name}"
            }
            @Suppress("UNCHECKED_CAST")
            return VocabViewModel(repository) as T
        }
    }
}

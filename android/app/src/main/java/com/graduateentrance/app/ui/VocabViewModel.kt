package com.graduateentrance.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.graduateentrance.app.data.VocabDictationResult
import com.graduateentrance.app.data.VocabEnrichResult
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
    val enriching: Boolean = false,
    val dictationActive: Boolean = false,
    val dictationLoading: Boolean = false,
    val dictationWords: List<VocabWordDto> = emptyList(),
    val dictationIndex: Int = 0,
    val dictationInput: String = "",
    val dictationChecked: Boolean = false,
    val dictationCorrectCount: Int = 0,
    val notice: String? = null,
    val error: String? = null,
) {
    val current: VocabWordDto? get() = queue.firstOrNull()
    val dictationCurrent: VocabWordDto? get() = dictationWords.getOrNull(dictationIndex)
    val dictationDone: Boolean get() =
        dictationWords.isNotEmpty() && dictationIndex >= dictationWords.size
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
        enrichCurrent()
    }

    private fun enrichCurrent() {
        val word = _uiState.value.current ?: return
        if (word.phonetic.isNotBlank() && word.exampleEn.isNotBlank()) return
        if (_uiState.value.enriching) return
        viewModelScope.launch {
            _uiState.update { it.copy(enriching = true) }
            val result = repository.enrich(word.id)
            _uiState.update { state ->
                when (result) {
                    is VocabEnrichResult.Enriched -> state.copy(
                        enriching = false,
                        queue = state.queue.map {
                            if (it.id == result.word.id) result.word else it
                        },
                    )
                    else -> state.copy(enriching = false)
                }
            }
        }
    }

    fun startDictation() {
        viewModelScope.launch {
            _uiState.update {
                it.copy(
                    dictationActive = true,
                    dictationLoading = true,
                    dictationWords = emptyList(),
                    dictationIndex = 0,
                    dictationInput = "",
                    dictationChecked = false,
                    dictationCorrectCount = 0,
                )
            }
            when (val result = repository.dictation()) {
                is VocabDictationResult.Loaded -> _uiState.update {
                    it.copy(
                        dictationLoading = false,
                        dictationWords = result.dictation.words.shuffled(),
                    )
                }
                VocabDictationResult.Offline -> _uiState.update {
                    it.copy(
                        dictationActive = false,
                        dictationLoading = false,
                        notice = "网络不可用，无法加载默写",
                    )
                }
                is VocabDictationResult.Rejected -> _uiState.update {
                    it.copy(
                        dictationActive = false,
                        dictationLoading = false,
                        notice = "默写加载失败（HTTP ${result.code}）",
                    )
                }
            }
        }
    }

    fun exitDictation() {
        _uiState.update { it.copy(dictationActive = false) }
    }

    fun setDictationInput(value: String) {
        _uiState.update { it.copy(dictationInput = value) }
    }

    fun checkDictation() {
        _uiState.update { state ->
            val word = state.dictationCurrent ?: return@update state
            val correct = state.dictationInput.trim().equals(word.word, ignoreCase = true)
            state.copy(
                dictationChecked = true,
                dictationCorrectCount = state.dictationCorrectCount + if (correct) 1 else 0,
            )
        }
    }

    fun nextDictation() {
        _uiState.update {
            it.copy(
                dictationIndex = it.dictationIndex + 1,
                dictationInput = "",
                dictationChecked = false,
            )
        }
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

package com.graduateentrance.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.graduateentrance.app.data.AppSettings
import com.graduateentrance.app.data.DictationTaskCheckInResult
import com.graduateentrance.app.data.VocabDictationResult
import com.graduateentrance.app.data.VocabDictationSubmitResult
import com.graduateentrance.app.data.VocabEnrichResult
import com.graduateentrance.app.data.VocabGradeActionResult
import com.graduateentrance.app.data.VocabLoadResult
import com.graduateentrance.app.data.VocabRepository
import com.graduateentrance.app.network.VocabWordDto
import java.time.LocalDate
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
    val dictationLastCorrect: Boolean = false,
    val dictationCorrectCount: Int = 0,
    val dictationRound: Int = 1,
    val dictationRetryQueue: List<VocabWordDto> = emptyList(),
    val dictationFirstTotal: Int = 0,
    val dictationTaskCheckedIn: Boolean = false,
    val dictationTotalToday: Int = 0,
    val dictationCorrectToday: Int = 0,
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

    private val gradedWordIds = mutableSetOf<String>()
    private val dictationCorrectIds = mutableSetOf<String>()
    private val dictationWrongIds = mutableSetOf<String>()
    private var dictationSubmitted = false
    private var dictationStartMs = 0L

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, error = null) }
            when (val result = repository.load(AppSettings.vocabNewLimit)) {
                is VocabLoadResult.Loaded -> {
                    gradedWordIds.clear()
                    val queue = result.today.dueWords + result.today.newWords
                    val reviewedToday = result.today.reviewedTodayCount
                    _uiState.update {
                        it.copy(
                            loading = false,
                            queue = queue,
                            revealed = false,
                            gradedCount = reviewedToday,
                            sessionTotal = reviewedToday + queue.size,
                            learnedCount = result.today.learnedCount,
                            totalCount = result.today.totalCount,
                            dueCount = result.today.dueCount,
                            dictationTotalToday = result.today.dictationTotalToday,
                            dictationCorrectToday = result.today.dictationCorrectToday,
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
            dictationCorrectIds.clear()
            dictationWrongIds.clear()
            dictationSubmitted = false
            dictationStartMs = System.currentTimeMillis()
            _uiState.update {
                it.copy(
                    dictationActive = true,
                    dictationLoading = true,
                    dictationWords = emptyList(),
                    dictationIndex = 0,
                    dictationInput = "",
                    dictationChecked = false,
                    dictationLastCorrect = false,
                    dictationCorrectCount = 0,
                    dictationRound = 1,
                    dictationRetryQueue = emptyList(),
                    dictationFirstTotal = 0,
                    dictationTaskCheckedIn = false,
                )
            }
            when (val result = repository.dictation()) {
                is VocabDictationResult.Loaded -> _uiState.update {
                    val words = result.dictation.words.shuffled()
                    it.copy(
                        dictationLoading = false,
                        dictationWords = words,
                        dictationFirstTotal = words.size,
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
        submitDictationResultIfNeeded()
        _uiState.update { it.copy(dictationActive = false) }
    }

    fun setDictationInput(value: String) {
        _uiState.update { it.copy(dictationInput = value) }
    }

    fun checkDictation() {
        val state = _uiState.value
        val word = state.dictationCurrent ?: return
        markDictation(
            word = word,
            correct = state.dictationInput.trim().equals(word.word, ignoreCase = true),
        )
    }

    fun giveUpDictation() {
        val word = _uiState.value.dictationCurrent ?: return
        markDictation(word = word, correct = false)
    }

    private fun markDictation(word: VocabWordDto, correct: Boolean) {
        val state = _uiState.value
        if (state.dictationChecked) return
        if (state.dictationRound == 1) {
            if (correct) dictationCorrectIds.add(word.id) else dictationWrongIds.add(word.id)
        }
        _uiState.update {
            it.copy(
                dictationChecked = true,
                dictationLastCorrect = correct,
                dictationCorrectCount = it.dictationCorrectCount +
                    if (correct && it.dictationRound == 1) 1 else 0,
                dictationRetryQueue = if (correct) {
                    it.dictationRetryQueue
                } else {
                    it.dictationRetryQueue + word
                },
            )
        }
    }

    fun nextDictation() {
        val state = _uiState.value
        val roundFinished = state.dictationIndex + 1 >= state.dictationWords.size
        if (!roundFinished) {
            _uiState.update {
                it.copy(
                    dictationIndex = it.dictationIndex + 1,
                    dictationInput = "",
                    dictationChecked = false,
                    dictationLastCorrect = false,
                )
            }
            return
        }
        if (state.dictationRound == 1) {
            submitDictationResultIfNeeded()
        }
        if (state.dictationRetryQueue.isNotEmpty()) {
            _uiState.update {
                it.copy(
                    dictationWords = it.dictationRetryQueue.shuffled(),
                    dictationRetryQueue = emptyList(),
                    dictationRound = it.dictationRound + 1,
                    dictationIndex = 0,
                    dictationInput = "",
                    dictationChecked = false,
                    dictationLastCorrect = false,
                )
            }
        } else {
            _uiState.update {
                it.copy(
                    dictationIndex = it.dictationIndex + 1,
                    dictationInput = "",
                    dictationChecked = false,
                    dictationLastCorrect = false,
                )
            }
            completeDictationTaskIfAny()
        }
    }

    private fun submitDictationResultIfNeeded() {
        if (dictationSubmitted) return
        if (dictationCorrectIds.isEmpty() && dictationWrongIds.isEmpty()) return
        dictationSubmitted = true
        viewModelScope.launch {
            when (
                val result = repository.submitDictation(
                    dictationCorrectIds.toList(),
                    dictationWrongIds.toList(),
                )
            ) {
                is VocabDictationSubmitResult.Submitted -> _uiState.update {
                    it.copy(
                        dictationTotalToday = result.result.total,
                        dictationCorrectToday = result.result.correct,
                    )
                }
                VocabDictationSubmitResult.Offline -> _uiState.update {
                    it.copy(notice = "网络不可用，默写结果未同步")
                }
                is VocabDictationSubmitResult.Rejected -> _uiState.update {
                    it.copy(notice = "默写结果同步失败（HTTP ${result.code}）")
                }
            }
        }
    }

    private fun completeDictationTaskIfAny() {
        viewModelScope.launch {
            val minutes = ((System.currentTimeMillis() - dictationStartMs) / 60000L)
                .toInt()
                .coerceAtLeast(1)
            val result = repository.completeDictationTask(
                LocalDate.now().toString(),
                minutes,
            )
            if (result is DictationTaskCheckInResult.Completed) {
                _uiState.update { it.copy(dictationTaskCheckedIn = true) }
            }
        }
    }

    fun grade(wordId: String, grade: String) {
        if (_uiState.value.grading) return
        if (wordId in gradedWordIds) {
            // 当天重现：首次评级已提交调度，这里只做本地复背
            _uiState.update { state ->
                if (grade == "mastered") {
                    state.copy(
                        queue = state.queue.filterNot { it.id == wordId },
                        revealed = false,
                    )
                } else {
                    state.copy(queue = requeue(state.queue, wordId), revealed = false)
                }
            }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(grading = true, notice = null) }
            when (val result = repository.grade(wordId, grade)) {
                is VocabGradeActionResult.Graded -> {
                    gradedWordIds.add(wordId)
                    _uiState.update { state ->
                        val mastered = grade == "mastered"
                        state.copy(
                            grading = false,
                            queue = if (mastered) {
                                state.queue.filterNot { it.id == wordId }
                            } else {
                                requeue(state.queue, wordId)
                            },
                            revealed = false,
                            gradedCount = state.gradedCount + 1,
                            learnedCount = if (result.result.word.reps == 1) {
                                state.learnedCount + 1
                            } else {
                                state.learnedCount
                            },
                            notice = if (mastered) {
                                "已评级，下次复习 ${result.result.dueDate}"
                            } else {
                                "稍后会再考这个词，直到你答「掌握」"
                            },
                        )
                    }
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

    private fun requeue(queue: List<VocabWordDto>, wordId: String): List<VocabWordDto> {
        val word = queue.firstOrNull { it.id == wordId } ?: return queue
        return queue.filterNot { it.id == wordId } + word
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

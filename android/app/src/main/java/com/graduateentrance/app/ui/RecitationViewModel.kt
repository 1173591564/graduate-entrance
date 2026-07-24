package com.graduateentrance.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.graduateentrance.app.data.DictationTaskCheckInResult
import com.graduateentrance.app.data.RecitationLoadResult
import com.graduateentrance.app.data.RecitationRepository
import com.graduateentrance.app.data.ReciteActionResult
import com.graduateentrance.app.network.RecitationGroupDto
import com.graduateentrance.app.network.RecitationItemDto
import com.graduateentrance.app.network.RecitationStatsDto
import java.time.LocalDate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class RecitationUiState(
    val loading: Boolean = true,
    val subject: String = "politics",
    val today: RecitationItemDto? = null,
    val queue: List<RecitationItemDto> = emptyList(),
    val revealed: Boolean = false,
    val queueGradedCount: Int = 0,
    val queueInitialSize: Int = 0,
    val taskCheckedIn: Boolean = false,
    val groups: List<RecitationGroupDto> = emptyList(),
    val stats: RecitationStatsDto? = null,
    val busy: Set<String> = emptySet(),
    val expanded: Set<String> = emptySet(),
    val notice: String? = null,
    val error: String? = null,
    val detailId: String? = null,
    val detailSelfTest: Boolean = false,
    val detailRevealed: Boolean = false,
) {
    val queueCurrent: RecitationItemDto? get() = queue.firstOrNull()

    val allItems: List<RecitationItemDto> get() = groups.flatMap { it.items }

    val detailItem: RecitationItemDto? get() = allItems.firstOrNull { it.id == detailId }

    val detailIndex: Int get() = allItems.indexOfFirst { it.id == detailId }
}

class RecitationViewModel(
    private val repository: RecitationRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(RecitationUiState())
    val uiState: StateFlow<RecitationUiState> = _uiState.asStateFlow()

    private var sessionStartMs = System.currentTimeMillis()
    private var taskCheckInAttempted = false

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, error = null) }
            when (val result = repository.load(_uiState.value.subject)) {
                is RecitationLoadResult.Loaded -> _uiState.update {
                    it.copy(
                        loading = false,
                        today = result.today,
                        queue = result.queue,
                        revealed = false,
                        queueGradedCount = 0,
                        queueInitialSize = result.queue.size,
                        groups = result.groups,
                        stats = result.stats,
                    )
                }
                RecitationLoadResult.Offline -> _uiState.update {
                    it.copy(loading = false, error = "网络不可用，请稍后重试")
                }
                is RecitationLoadResult.Rejected -> _uiState.update {
                    it.copy(loading = false, error = "加载失败（HTTP ${result.code}）")
                }
            }
        }
    }

    fun switchSubject(subject: String) {
        if (_uiState.value.subject == subject) return
        _uiState.update { it.copy(subject = subject, expanded = emptySet()) }
        refresh()
    }

    fun reveal() {
        _uiState.update { it.copy(revealed = true) }
    }

    fun gradeCurrent(grade: String) {
        val item = _uiState.value.queueCurrent ?: return
        gradeItem(item, grade)
    }

    private fun gradeItem(item: RecitationItemDto, grade: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(busy = it.busy + item.id, notice = null) }
            when (val result = repository.recite(item.id, undo = false, grade = grade)) {
                is ReciteActionResult.Updated -> {
                    val updated = result.item
                    val wasQueued = _uiState.value.queue.any { it.id == item.id }
                    val remaining = _uiState.value.queue.filterNot { it.id == item.id }
                    _uiState.update {
                        it.copy(
                            busy = it.busy - item.id,
                            queue = remaining,
                            revealed = false,
                            queueGradedCount = it.queueGradedCount + if (wasQueued) 1 else 0,
                            today = if (it.today?.id == updated.id) updated else it.today,
                            groups = it.groups.map { group ->
                                group.copy(
                                    items = group.items.map { row ->
                                        if (row.id == updated.id) updated else row
                                    },
                                )
                            },
                            stats = it.stats?.copy(
                                recitedToday = it.stats.recitedToday +
                                    if (!item.recitedToday) 1 else 0,
                            ),
                            detailSelfTest = false,
                            detailRevealed = false,
                        )
                    }
                    if (wasQueued && remaining.isEmpty()) {
                        completeMemorizationTaskIfAny()
                    }
                }
                ReciteActionResult.Offline -> _uiState.update {
                    it.copy(busy = it.busy - item.id, notice = "网络不可用，未保存")
                }
                is ReciteActionResult.Rejected -> _uiState.update {
                    it.copy(busy = it.busy - item.id, notice = "提交失败（HTTP ${result.code}）")
                }
            }
        }
    }

    fun openDetail(itemId: String) {
        _uiState.update {
            it.copy(detailId = itemId, detailSelfTest = false, detailRevealed = false)
        }
    }

    fun closeDetail() {
        _uiState.update {
            it.copy(detailId = null, detailSelfTest = false, detailRevealed = false)
        }
    }

    fun moveDetail(delta: Int) {
        val state = _uiState.value
        val items = state.allItems
        val index = state.detailIndex
        if (index < 0) return
        val next = items.getOrNull(index + delta) ?: return
        _uiState.update {
            it.copy(detailId = next.id, detailSelfTest = false, detailRevealed = false)
        }
    }

    fun startDetailSelfTest() {
        _uiState.update { it.copy(detailSelfTest = true, detailRevealed = false) }
    }

    fun revealDetail() {
        _uiState.update { it.copy(detailRevealed = true) }
    }

    fun gradeDetail(grade: String) {
        val item = _uiState.value.detailItem ?: return
        gradeItem(item, grade)
    }

    private fun completeMemorizationTaskIfAny() {
        if (taskCheckInAttempted) return
        taskCheckInAttempted = true
        viewModelScope.launch {
            val minutes = ((System.currentTimeMillis() - sessionStartMs) / 60000L)
                .toInt()
                .coerceAtLeast(1)
            val result = repository.completeMemorizationTask(
                LocalDate.now().toString(),
                minutes,
            )
            if (result is DictationTaskCheckInResult.Completed) {
                _uiState.update {
                    it.copy(taskCheckedIn = true, notice = "已自动打卡今日背诵任务")
                }
            }
        }
    }

    fun recite(itemId: String, undo: Boolean = false) {
        viewModelScope.launch {
            _uiState.update { it.copy(busy = it.busy + itemId, notice = null) }
            when (val result = repository.recite(itemId, undo)) {
                is ReciteActionResult.Updated -> {
                    _uiState.update { it.copy(busy = it.busy - itemId) }
                    refresh()
                }
                ReciteActionResult.Offline -> _uiState.update {
                    it.copy(busy = it.busy - itemId, notice = "网络不可用，打卡未保存")
                }
                is ReciteActionResult.Rejected -> _uiState.update {
                    it.copy(busy = it.busy - itemId, notice = "打卡失败（HTTP ${result.code}）")
                }
            }
        }
    }

    fun toggleExpanded(itemId: String) {
        _uiState.update {
            val next = if (itemId in it.expanded) it.expanded - itemId else it.expanded + itemId
            it.copy(expanded = next)
        }
    }

    fun consumeNotice() {
        _uiState.update { it.copy(notice = null) }
    }

    class Factory(
        private val repository: RecitationRepository,
    ) : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            require(modelClass.isAssignableFrom(RecitationViewModel::class.java)) {
                "Unknown ViewModel class: ${modelClass.name}"
            }
            @Suppress("UNCHECKED_CAST")
            return RecitationViewModel(repository) as T
        }
    }
}

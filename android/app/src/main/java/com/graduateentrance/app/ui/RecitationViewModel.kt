package com.graduateentrance.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.graduateentrance.app.data.RecitationLoadResult
import com.graduateentrance.app.data.RecitationRepository
import com.graduateentrance.app.data.ReciteActionResult
import com.graduateentrance.app.network.RecitationGroupDto
import com.graduateentrance.app.network.RecitationItemDto
import com.graduateentrance.app.network.RecitationStatsDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class RecitationUiState(
    val loading: Boolean = true,
    val subject: String = "politics",
    val today: RecitationItemDto? = null,
    val groups: List<RecitationGroupDto> = emptyList(),
    val stats: RecitationStatsDto? = null,
    val busy: Set<String> = emptySet(),
    val expanded: Set<String> = emptySet(),
    val notice: String? = null,
    val error: String? = null,
)

class RecitationViewModel(
    private val repository: RecitationRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(RecitationUiState())
    val uiState: StateFlow<RecitationUiState> = _uiState.asStateFlow()

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

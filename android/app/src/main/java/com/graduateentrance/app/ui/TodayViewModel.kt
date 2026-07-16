package com.graduateentrance.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.graduateentrance.app.data.CheckInResult
import com.graduateentrance.app.data.TodayRepository
import com.graduateentrance.app.data.local.TodayTaskEntity
import java.time.LocalDate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

data class TodayUiState(
    val date: LocalDate = LocalDate.now(),
    val loading: Boolean = true,
    val fromCache: Boolean = false,
    val pendingCheckIns: Int = 0,
    val plannedMinutes: Int = 0,
    val completedMinutes: Int = 0,
    val remainingMinutes: Int = 0,
    val tasks: List<TodayTaskEntity> = emptyList(),
    val notice: String? = null,
)

class TodayViewModel(private val repository: TodayRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(TodayUiState())
    val uiState: StateFlow<TodayUiState> = _uiState.asStateFlow()

    private val syncMutex = Mutex()

    init {
        refresh()
    }

    fun selectDate(date: LocalDate) {
        _uiState.update { it.copy(date = date) }
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, notice = null) }
            val snapshot = repository.loadToday(_uiState.value.date.toString())
            _uiState.update {
                it.copy(
                    loading = false,
                    fromCache = snapshot.fromCache,
                    pendingCheckIns = snapshot.pendingCheckIns,
                    plannedMinutes = snapshot.plannedMinutes,
                    completedMinutes = snapshot.completedMinutes,
                    remainingMinutes = snapshot.remainingMinutes,
                    tasks = snapshot.tasks,
                )
            }
        }
    }

    fun checkIn(taskId: String, actualMinutes: Int) {
        viewModelScope.launch {
            val notice = when (val result = repository.checkIn(taskId, actualMinutes)) {
                CheckInResult.Synced -> "打卡成功"
                CheckInResult.Queued -> "网络不可用，打卡已入队，恢复后自动同步"
                is CheckInResult.Rejected -> "打卡失败（HTTP ${result.code}）"
            }
            _uiState.update { it.copy(notice = notice) }
            refresh()
        }
    }

    fun onNetworkAvailable() {
        viewModelScope.launch {
            syncMutex.withLock {
                if (!repository.hasPendingCheckIns()) {
                    return@withLock
                }
                val synced = repository.syncPendingCheckIns()
                if (synced > 0) {
                    _uiState.update { it.copy(notice = "已同步 $synced 条离线打卡") }
                }
            }
            refresh()
        }
    }

    class Factory(private val repository: TodayRepository) : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            require(modelClass.isAssignableFrom(TodayViewModel::class.java)) {
                "Unknown ViewModel class: ${modelClass.name}"
            }
            @Suppress("UNCHECKED_CAST")
            return TodayViewModel(repository) as T
        }
    }
}

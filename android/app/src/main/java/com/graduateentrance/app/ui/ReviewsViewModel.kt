package com.graduateentrance.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.graduateentrance.app.data.GradeResult
import com.graduateentrance.app.data.ReviewsLoadResult
import com.graduateentrance.app.data.ReviewsRepository
import com.graduateentrance.app.network.ReviewProblemDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ReviewsUiState(
    val loading: Boolean = true,
    val includeDrafts: Boolean = true,
    val asOf: String = "",
    val total: Int = 0,
    val sessionTotal: Int = 0,
    val reviewedCount: Int = 0,
    val problems: List<ReviewProblemDto> = emptyList(),
    val grading: Set<String> = emptySet(),
    val notice: String? = null,
    val error: String? = null,
)

class ReviewsViewModel(private val repository: ReviewsRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(ReviewsUiState())
    val uiState: StateFlow<ReviewsUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun setIncludeDrafts(includeDrafts: Boolean) {
        _uiState.update { it.copy(includeDrafts = includeDrafts) }
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, error = null) }
            when (val result = repository.loadDueReviews(_uiState.value.includeDrafts)) {
                is ReviewsLoadResult.Loaded -> _uiState.update {
                    it.copy(
                        loading = false,
                        asOf = result.asOf,
                        total = result.total,
                        sessionTotal = result.problems.size,
                        reviewedCount = 0,
                        problems = result.problems,
                    )
                }
                ReviewsLoadResult.Offline -> _uiState.update {
                    it.copy(loading = false, error = "网络不可用，请稍后重试")
                }
                is ReviewsLoadResult.Rejected -> _uiState.update {
                    it.copy(loading = false, error = "加载失败（HTTP ${result.code}）")
                }
            }
        }
    }

    fun grade(problemId: String, grade: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(grading = it.grading + problemId, notice = null) }
            when (val result = repository.grade(problemId, grade)) {
                is GradeResult.Graded -> _uiState.update { state ->
                    state.copy(
                        grading = state.grading - problemId,
                        problems = state.problems.filterNot { it.id == problemId },
                        total = (state.total - 1).coerceAtLeast(0),
                        reviewedCount = state.reviewedCount + 1,
                        notice = "已评级，下次复习 ${result.result.dueDate}" +
                            "（间隔 ${result.result.intervalDays} 天）",
                    )
                }
                GradeResult.Offline -> _uiState.update {
                    it.copy(grading = it.grading - problemId, notice = "网络不可用，评级未提交")
                }
                is GradeResult.Rejected -> _uiState.update {
                    it.copy(
                        grading = it.grading - problemId,
                        notice = "评级失败（HTTP ${result.code}）",
                    )
                }
            }
        }
    }

    fun consumeNotice() {
        _uiState.update { it.copy(notice = null) }
    }

    class Factory(private val repository: ReviewsRepository) : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            require(modelClass.isAssignableFrom(ReviewsViewModel::class.java)) {
                "Unknown ViewModel class: ${modelClass.name}"
            }
            @Suppress("UNCHECKED_CAST")
            return ReviewsViewModel(repository) as T
        }
    }
}

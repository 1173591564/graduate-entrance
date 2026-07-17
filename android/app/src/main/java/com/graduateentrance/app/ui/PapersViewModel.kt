package com.graduateentrance.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.graduateentrance.app.data.PaperDownloadResult
import com.graduateentrance.app.data.PaperStatusResult
import com.graduateentrance.app.data.PapersLoadResult
import com.graduateentrance.app.data.PapersRepository
import com.graduateentrance.app.network.PaperDto
import com.graduateentrance.app.network.PaperGroupDto
import com.graduateentrance.app.network.PaperStatsDto
import java.io.File
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class PapersUiState(
    val loading: Boolean = true,
    val today: PaperDto? = null,
    val groups: List<PaperGroupDto> = emptyList(),
    val stats: PaperStatsDto? = null,
    val busy: Set<String> = emptySet(),
    val notice: String? = null,
    val error: String? = null,
    val viewer: PdfViewerTarget? = null,
)

data class PdfViewerTarget(val file: File, val title: String)

class PapersViewModel(
    private val repository: PapersRepository,
    private val cacheDir: File,
) : ViewModel() {
    private val _uiState = MutableStateFlow(PapersUiState())
    val uiState: StateFlow<PapersUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, error = null) }
            when (val result = repository.load()) {
                is PapersLoadResult.Loaded -> _uiState.update {
                    it.copy(
                        loading = false,
                        today = result.today,
                        groups = result.groups,
                        stats = result.stats,
                    )
                }
                PapersLoadResult.Offline -> _uiState.update {
                    it.copy(loading = false, error = "网络不可用，请稍后重试")
                }
                is PapersLoadResult.Rejected -> _uiState.update {
                    it.copy(loading = false, error = "加载失败（HTTP ${result.code}）")
                }
            }
        }
    }

    fun setStatus(paperId: String, status: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(busy = it.busy + paperId, notice = null) }
            when (val result = repository.setStatus(paperId, status)) {
                is PaperStatusResult.Updated -> {
                    _uiState.update { it.copy(busy = it.busy - paperId) }
                    refresh()
                }
                PaperStatusResult.Offline -> _uiState.update {
                    it.copy(busy = it.busy - paperId, notice = "网络不可用，状态未更新")
                }
                is PaperStatusResult.Rejected -> _uiState.update {
                    it.copy(busy = it.busy - paperId, notice = "更新失败（HTTP ${result.code}）")
                }
            }
        }
    }

    fun openPaper(paper: PaperDto) {
        viewModelScope.launch {
            _uiState.update { it.copy(busy = it.busy + paper.id, notice = null) }
            val target = File(File(cacheDir, "papers"), "${paper.id}.pdf")
            when (val result = repository.download(paper.id, target)) {
                is PaperDownloadResult.Ready -> _uiState.update {
                    it.copy(
                        busy = it.busy - paper.id,
                        viewer = PdfViewerTarget(result.file, paper.title),
                    )
                }
                PaperDownloadResult.Offline -> _uiState.update {
                    it.copy(busy = it.busy - paper.id, notice = "网络不可用，无法打开 PDF")
                }
                is PaperDownloadResult.Rejected -> _uiState.update {
                    it.copy(
                        busy = it.busy - paper.id,
                        notice = "PDF 打开失败（HTTP ${result.code}）",
                    )
                }
            }
        }
    }

    fun closeViewer() {
        _uiState.update { it.copy(viewer = null) }
    }

    fun consumeNotice() {
        _uiState.update { it.copy(notice = null) }
    }

    class Factory(
        private val repository: PapersRepository,
        private val cacheDir: File,
    ) : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            require(modelClass.isAssignableFrom(PapersViewModel::class.java)) {
                "Unknown ViewModel class: ${modelClass.name}"
            }
            @Suppress("UNCHECKED_CAST")
            return PapersViewModel(repository, cacheDir) as T
        }
    }
}

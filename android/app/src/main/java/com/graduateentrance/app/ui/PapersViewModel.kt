package com.graduateentrance.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.graduateentrance.app.data.PaperAnnotationResult
import com.graduateentrance.app.data.PaperContentAnnotation
import com.graduateentrance.app.data.PaperContentBlock
import com.graduateentrance.app.data.PaperContentTocEntry
import com.graduateentrance.app.data.PaperContentResult
import com.graduateentrance.app.data.PaperDownloadResult
import com.graduateentrance.app.data.PaperStatusResult
import com.graduateentrance.app.data.PapersLoadResult
import com.graduateentrance.app.data.PapersRepository
import com.graduateentrance.app.data.ReadingProgressStore
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
    val reader: ReaderState? = null,
)

data class PdfViewerTarget(val file: File, val title: String)

data class ReaderState(
    val paper: PaperDto,
    val loading: Boolean = true,
    val blocks: List<PaperContentBlock> = emptyList(),
    val toc: List<PaperContentTocEntry> = emptyList(),
    val annotations: List<PaperContentAnnotation> = emptyList(),
    val initialBlockIndex: Int = 0,
    val error: String? = null,
)

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

    fun openReader(paper: PaperDto) {
        _uiState.update {
            it.copy(
                reader = ReaderState(
                    paper = paper,
                    initialBlockIndex = ReadingProgressStore.restore(paper.id),
                ),
            )
        }
        viewModelScope.launch {
            val result = repository.content(paper.id)
            _uiState.update { state ->
                val reader = state.reader ?: return@update state
                if (reader.paper.id != paper.id) return@update state
                when (result) {
                    is PaperContentResult.Loaded -> state.copy(
                        reader = reader.copy(
                            loading = false,
                            blocks = result.blocks,
                            toc = result.toc,
                            annotations = result.annotations,
                        ),
                    )
                    PaperContentResult.Offline -> state.copy(
                        reader = reader.copy(loading = false, error = "网络不可用，请稍后重试"),
                    )
                    is PaperContentResult.Rejected -> state.copy(
                        reader = reader.copy(
                            loading = false,
                            error = if (result.code == 404) {
                                "这篇论文还没解析正文"
                            } else {
                                "加载失败（HTTP ${result.code}）"
                            },
                        ),
                    )
                }
            }
        }
    }

    fun closeReader() {
        _uiState.update { it.copy(reader = null) }
    }

    fun saveReadingProgress(blockIndex: Int) {
        val paperId = _uiState.value.reader?.paper?.id ?: return
        ReadingProgressStore.save(paperId, blockIndex)
    }

    fun addAnnotation(blockIndex: Int, excerpt: String, note: String, color: String) {
        val paperId = _uiState.value.reader?.paper?.id ?: return
        viewModelScope.launch {
            when (val result = repository.addAnnotation(paperId, blockIndex, excerpt, note, color)) {
                is PaperAnnotationResult.Saved -> _uiState.update { state ->
                    val reader = state.reader ?: return@update state
                    state.copy(
                        reader = reader.copy(annotations = reader.annotations + result.annotation),
                    )
                }
                PaperAnnotationResult.Deleted -> Unit
                PaperAnnotationResult.Offline -> _uiState.update {
                    it.copy(notice = "网络不可用，标注未保存")
                }
                is PaperAnnotationResult.Rejected -> _uiState.update {
                    it.copy(notice = "标注保存失败（HTTP ${result.code}）")
                }
            }
        }
    }

    fun updateAnnotation(annotationId: String, note: String?, color: String?) {
        viewModelScope.launch {
            when (val result = repository.updateAnnotation(annotationId, note, color)) {
                is PaperAnnotationResult.Saved -> _uiState.update { state ->
                    val reader = state.reader ?: return@update state
                    state.copy(
                        reader = reader.copy(
                            annotations = reader.annotations.map {
                                if (it.id == annotationId) result.annotation else it
                            },
                        ),
                    )
                }
                PaperAnnotationResult.Deleted -> Unit
                PaperAnnotationResult.Offline -> _uiState.update {
                    it.copy(notice = "网络不可用，标注未更新")
                }
                is PaperAnnotationResult.Rejected -> _uiState.update {
                    it.copy(notice = "标注更新失败（HTTP ${result.code}）")
                }
            }
        }
    }

    fun deleteAnnotation(annotationId: String) {
        viewModelScope.launch {
            when (val result = repository.deleteAnnotation(annotationId)) {
                PaperAnnotationResult.Deleted -> _uiState.update { state ->
                    val reader = state.reader ?: return@update state
                    state.copy(
                        reader = reader.copy(
                            annotations = reader.annotations.filterNot { it.id == annotationId },
                        ),
                    )
                }
                is PaperAnnotationResult.Saved -> Unit
                PaperAnnotationResult.Offline -> _uiState.update {
                    it.copy(notice = "网络不可用，标注未删除")
                }
                is PaperAnnotationResult.Rejected -> _uiState.update {
                    it.copy(notice = "标注删除失败（HTTP ${result.code}）")
                }
            }
        }
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

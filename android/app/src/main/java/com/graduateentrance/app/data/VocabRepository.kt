package com.graduateentrance.app.data

import com.graduateentrance.app.network.GraduateEntranceApi
import com.graduateentrance.app.network.TaskCompletionRequest
import com.graduateentrance.app.network.TodayTaskDto
import com.graduateentrance.app.network.VocabDictationDto
import com.graduateentrance.app.network.VocabDictationResultDto
import com.graduateentrance.app.network.VocabDictationResultRequest
import com.graduateentrance.app.network.VocabGradeRequest
import com.graduateentrance.app.network.VocabGradeResultDto
import com.graduateentrance.app.network.VocabTodayDto
import com.graduateentrance.app.network.VocabWordDto
import java.io.IOException
import retrofit2.HttpException

sealed interface VocabLoadResult {
    data class Loaded(val today: VocabTodayDto) : VocabLoadResult
    data object Offline : VocabLoadResult
    data class Rejected(val code: Int) : VocabLoadResult
}

sealed interface VocabGradeActionResult {
    data class Graded(val result: VocabGradeResultDto) : VocabGradeActionResult
    data object Offline : VocabGradeActionResult
    data class Rejected(val code: Int) : VocabGradeActionResult
}

sealed interface VocabDictationResult {
    data class Loaded(val dictation: VocabDictationDto) : VocabDictationResult
    data object Offline : VocabDictationResult
    data class Rejected(val code: Int) : VocabDictationResult
}

sealed interface VocabDictationSubmitResult {
    data class Submitted(val result: VocabDictationResultDto) : VocabDictationSubmitResult
    data object Offline : VocabDictationSubmitResult
    data class Rejected(val code: Int) : VocabDictationSubmitResult
}

sealed interface DictationTaskCheckInResult {
    data class Completed(val task: TodayTaskDto) : DictationTaskCheckInResult
    data object NoTask : DictationTaskCheckInResult
    data object Offline : DictationTaskCheckInResult
    data class Rejected(val code: Int) : DictationTaskCheckInResult
}

sealed interface VocabEnrichResult {
    data class Enriched(val word: VocabWordDto) : VocabEnrichResult
    data object Offline : VocabEnrichResult
    data class Rejected(val code: Int) : VocabEnrichResult
}

class VocabRepository(private val api: GraduateEntranceApi) {
    suspend fun load(newLimit: Int): VocabLoadResult =
        try {
            VocabLoadResult.Loaded(api.vocabToday(newLimit))
        } catch (_: IOException) {
            VocabLoadResult.Offline
        } catch (error: HttpException) {
            VocabLoadResult.Rejected(error.code())
        }

    suspend fun grade(wordId: String, grade: String): VocabGradeActionResult =
        try {
            VocabGradeActionResult.Graded(api.gradeVocabWord(wordId, VocabGradeRequest(grade)))
        } catch (_: IOException) {
            VocabGradeActionResult.Offline
        } catch (error: HttpException) {
            VocabGradeActionResult.Rejected(error.code())
        }

    suspend fun dictation(): VocabDictationResult =
        try {
            VocabDictationResult.Loaded(api.vocabDictation())
        } catch (_: IOException) {
            VocabDictationResult.Offline
        } catch (error: HttpException) {
            VocabDictationResult.Rejected(error.code())
        }

    suspend fun submitDictation(
        correctWordIds: List<String>,
        wrongWordIds: List<String>,
    ): VocabDictationSubmitResult =
        try {
            VocabDictationSubmitResult.Submitted(
                api.submitVocabDictationResult(
                    VocabDictationResultRequest(
                        correctWordIds = correctWordIds,
                        wrongWordIds = wrongWordIds,
                    ),
                ),
            )
        } catch (_: IOException) {
            VocabDictationSubmitResult.Offline
        } catch (error: HttpException) {
            VocabDictationSubmitResult.Rejected(error.code())
        }

    suspend fun completeDictationTask(
        date: String,
        actualMinutes: Int,
    ): DictationTaskCheckInResult =
        try {
            val today = api.today(date)
            val task = today.tasks.firstOrNull {
                it.studyModule == "vocab" && it.status == "pending"
            }
            if (task == null) {
                DictationTaskCheckInResult.NoTask
            } else {
                DictationTaskCheckInResult.Completed(
                    api.completeTask(task.id, TaskCompletionRequest(actualMinutes)),
                )
            }
        } catch (_: IOException) {
            DictationTaskCheckInResult.Offline
        } catch (error: HttpException) {
            DictationTaskCheckInResult.Rejected(error.code())
        }

    suspend fun enrich(wordId: String): VocabEnrichResult =
        try {
            VocabEnrichResult.Enriched(api.enrichVocabWord(wordId))
        } catch (_: IOException) {
            VocabEnrichResult.Offline
        } catch (error: HttpException) {
            VocabEnrichResult.Rejected(error.code())
        }
}

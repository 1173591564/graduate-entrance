package com.graduateentrance.app.data

import com.graduateentrance.app.network.GraduateEntranceApi
import com.graduateentrance.app.network.VocabDictationDto
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

sealed interface VocabEnrichResult {
    data class Enriched(val word: VocabWordDto) : VocabEnrichResult
    data object Offline : VocabEnrichResult
    data class Rejected(val code: Int) : VocabEnrichResult
}

class VocabRepository(private val api: GraduateEntranceApi) {
    suspend fun load(): VocabLoadResult =
        try {
            VocabLoadResult.Loaded(api.vocabToday())
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

    suspend fun enrich(wordId: String): VocabEnrichResult =
        try {
            VocabEnrichResult.Enriched(api.enrichVocabWord(wordId))
        } catch (_: IOException) {
            VocabEnrichResult.Offline
        } catch (error: HttpException) {
            VocabEnrichResult.Rejected(error.code())
        }
}

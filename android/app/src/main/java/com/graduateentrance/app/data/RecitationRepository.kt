package com.graduateentrance.app.data

import com.graduateentrance.app.network.GraduateEntranceApi
import com.graduateentrance.app.network.RecitationGroupDto
import com.graduateentrance.app.network.RecitationItemDto
import com.graduateentrance.app.network.RecitationStatsDto
import com.graduateentrance.app.network.ReciteRequest
import com.graduateentrance.app.network.TaskCompletionRequest
import java.io.IOException
import retrofit2.HttpException

sealed interface RecitationLoadResult {
    data class Loaded(
        val today: RecitationItemDto?,
        val queue: List<RecitationItemDto>,
        val groups: List<RecitationGroupDto>,
        val stats: RecitationStatsDto,
    ) : RecitationLoadResult
    data object Offline : RecitationLoadResult
    data class Rejected(val code: Int) : RecitationLoadResult
}

sealed interface ReciteActionResult {
    data class Updated(val item: RecitationItemDto) : ReciteActionResult
    data object Offline : ReciteActionResult
    data class Rejected(val code: Int) : ReciteActionResult
}

class RecitationRepository(private val api: GraduateEntranceApi) {
    suspend fun load(subject: String?): RecitationLoadResult =
        try {
            val today = api.recitationToday(subject)
            val list = api.recitations(subject)
            RecitationLoadResult.Loaded(today.item, today.queue, list.groups, list.stats)
        } catch (_: IOException) {
            RecitationLoadResult.Offline
        } catch (error: HttpException) {
            RecitationLoadResult.Rejected(error.code())
        }

    suspend fun recite(
        itemId: String,
        undo: Boolean,
        grade: String? = null,
    ): ReciteActionResult =
        try {
            ReciteActionResult.Updated(api.reciteItem(itemId, ReciteRequest(undo, grade)).item)
        } catch (_: IOException) {
            ReciteActionResult.Offline
        } catch (error: HttpException) {
            ReciteActionResult.Rejected(error.code())
        }

    suspend fun completeMemorizationTask(
        date: String,
        actualMinutes: Int,
    ): DictationTaskCheckInResult =
        try {
            val today = api.today(date)
            val task = today.tasks.firstOrNull {
                it.studyModule == "recitation" && it.status == "pending"
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
}

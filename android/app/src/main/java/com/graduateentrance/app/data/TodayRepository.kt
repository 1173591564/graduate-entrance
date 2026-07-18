package com.graduateentrance.app.data

import com.graduateentrance.app.data.local.PendingCheckInEntity
import com.graduateentrance.app.data.local.TodayDao
import com.graduateentrance.app.data.local.TodayTaskEntity
import com.graduateentrance.app.network.GraduateEntranceApi
import com.graduateentrance.app.network.TaskCompletionRequest
import com.graduateentrance.app.network.TaskUpdateRequest
import java.io.IOException
import retrofit2.HttpException

data class TodaySnapshot(
    val date: String,
    val plannedMinutes: Int,
    val completedMinutes: Int,
    val remainingMinutes: Int,
    val tasks: List<TodayTaskEntity>,
    val fromCache: Boolean,
    val pendingCheckIns: Int,
)

sealed interface CheckInResult {
    data object Synced : CheckInResult
    data object Queued : CheckInResult
    data class Rejected(val code: Int) : CheckInResult
}

class TodayRepository(
    private val api: GraduateEntranceApi,
    private val dao: TodayDao,
) {
    suspend fun loadToday(date: String): TodaySnapshot {
        val fromCache = try {
            val remote = api.today(date)
            dao.replaceDay(
                date,
                remote.tasks.map { task ->
                    TodayTaskEntity(
                        id = task.id,
                        plannedDate = task.plannedDate,
                        subjectName = task.subjectName,
                        knowledgePointName = task.knowledgePointName,
                        title = task.title,
                        estMinutes = task.estMinutes,
                        status = task.status,
                        actualMinutes = task.actualMinutes,
                        carryCount = task.carryCount,
                        taskOrder = task.order,
                        studyModule = task.studyModule,
                    )
                },
            )
            false
        } catch (_: IOException) {
            true
        }
        val pending = dao.pendingCheckIns()
        val pendingById = pending.associateBy { it.taskId }
        val tasks = dao.tasksFor(date).map { task ->
            val queued = pendingById[task.id]
            if (queued != null && task.status != "completed") {
                task.copy(status = "completed", actualMinutes = queued.actualMinutes)
            } else {
                task
            }
        }
        return buildSnapshot(date, tasks, fromCache, pending.size)
    }

    suspend fun checkIn(taskId: String, actualMinutes: Int): CheckInResult =
        try {
            api.completeTask(taskId, TaskCompletionRequest(actualMinutes))
            dao.markCompleted(taskId, actualMinutes)
            dao.removeCheckIn(taskId)
            CheckInResult.Synced
        } catch (_: IOException) {
            dao.enqueueCheckIn(
                PendingCheckInEntity(
                    taskId = taskId,
                    actualMinutes = actualMinutes,
                    queuedAt = System.currentTimeMillis(),
                ),
            )
            CheckInResult.Queued
        } catch (error: HttpException) {
            CheckInResult.Rejected(error.code())
        }

    suspend fun updateEstimate(taskId: String, estMinutes: Int): Boolean =
        try {
            api.updateTask(taskId, TaskUpdateRequest(estMinutes))
            dao.updateEstimate(taskId, estMinutes)
            true
        } catch (_: IOException) {
            false
        } catch (_: HttpException) {
            false
        }

    suspend fun syncPendingCheckIns(): Int {
        var synced = 0
        for (pending in dao.pendingCheckIns()) {
            try {
                api.completeTask(pending.taskId, TaskCompletionRequest(pending.actualMinutes))
                dao.markCompleted(pending.taskId, pending.actualMinutes)
                dao.removeCheckIn(pending.taskId)
                synced += 1
            } catch (_: IOException) {
                break
            } catch (_: HttpException) {
                dao.removeCheckIn(pending.taskId)
            }
        }
        return synced
    }

    suspend fun hasPendingCheckIns(): Boolean = dao.pendingCheckIns().isNotEmpty()

    private fun buildSnapshot(
        date: String,
        tasks: List<TodayTaskEntity>,
        fromCache: Boolean,
        pendingCount: Int,
    ): TodaySnapshot {
        val planned = tasks.filter { it.status != "skipped" }.sumOf { it.estMinutes }
        val completed = tasks
            .filter { it.status == "completed" }
            .sumOf { it.actualMinutes ?: it.estMinutes }
        val remaining = tasks.filter { it.status == "planned" }.sumOf { it.estMinutes }
        return TodaySnapshot(
            date = date,
            plannedMinutes = planned,
            completedMinutes = completed,
            remainingMinutes = remaining,
            tasks = tasks,
            fromCache = fromCache,
            pendingCheckIns = pendingCount,
        )
    }
}

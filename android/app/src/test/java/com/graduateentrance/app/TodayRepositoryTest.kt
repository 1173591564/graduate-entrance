package com.graduateentrance.app

import com.graduateentrance.app.data.CheckInResult
import com.graduateentrance.app.data.TodayRepository
import com.graduateentrance.app.data.local.PendingCheckInEntity
import com.graduateentrance.app.data.local.TodayDao
import com.graduateentrance.app.data.local.TodayTaskEntity
import com.graduateentrance.app.network.DueReviewsDto
import com.graduateentrance.app.network.GraduateEntranceApi
import com.graduateentrance.app.network.ReviewRequest
import com.graduateentrance.app.network.ReviewResultDto
import com.graduateentrance.app.network.ServiceStatus
import com.graduateentrance.app.network.TaskCompletionRequest
import com.graduateentrance.app.network.TodayDto
import com.graduateentrance.app.network.TodayTaskDto
import java.io.IOException
import kotlinx.coroutines.test.runTest
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response

private class FakeDao : TodayDao {
    val tasks = mutableMapOf<String, TodayTaskEntity>()
    val queue = mutableMapOf<String, PendingCheckInEntity>()

    override suspend fun tasksFor(date: String): List<TodayTaskEntity> =
        tasks.values.filter { it.plannedDate == date }.sortedWith(compareBy({ it.taskOrder }, { it.id }))

    override suspend fun deleteTasksFor(date: String) {
        tasks.values.filter { it.plannedDate == date }.forEach { tasks.remove(it.id) }
    }

    override suspend fun insertTasks(tasks: List<TodayTaskEntity>) {
        tasks.forEach { this.tasks[it.id] = it }
    }

    override suspend fun markCompleted(taskId: String, actualMinutes: Int) {
        tasks[taskId]?.let {
            tasks[taskId] = it.copy(status = "completed", actualMinutes = actualMinutes)
        }
    }

    override suspend fun pendingCheckIns(): List<PendingCheckInEntity> =
        queue.values.sortedWith(compareBy({ it.queuedAt }, { it.taskId }))

    override suspend fun enqueueCheckIn(checkIn: PendingCheckInEntity) {
        queue[checkIn.taskId] = checkIn
    }

    override suspend fun removeCheckIn(taskId: String) {
        queue.remove(taskId)
    }
}

private class FakeApi : GraduateEntranceApi {
    var offline = false
    var todayResponse: TodayDto? = null
    var rejectWith: Int? = null
    val completions = mutableListOf<Pair<String, Int>>()

    override suspend fun ping(): ServiceStatus = ServiceStatus("ok", "test", "test")

    override suspend fun today(date: String): TodayDto {
        if (offline) throw IOException("offline")
        return todayResponse ?: TodayDto(date, 0, 0, 0, emptyList())
    }

    override suspend fun completeTask(taskId: String, payload: TaskCompletionRequest): TodayTaskDto {
        if (offline) throw IOException("offline")
        rejectWith?.let { code ->
            throw HttpException(
                Response.error<TodayTaskDto>(
                    code,
                    "{}".toResponseBody("application/json".toMediaType()),
                ),
            )
        }
        completions.add(taskId to payload.actualMinutes)
        return TodayTaskDto(
            id = taskId,
            subjectName = "s",
            knowledgePointName = "kp",
            title = "t",
            plannedDate = "2026-08-05",
            estMinutes = 60,
            status = "completed",
            actualMinutes = payload.actualMinutes,
            carryCount = 0,
            order = 0,
        )
    }

    override suspend fun dueReviews(includeDrafts: Boolean, limit: Int): DueReviewsDto =
        DueReviewsDto(0, "2026-08-05", emptyList())

    override suspend fun reviewProblem(problemId: String, payload: ReviewRequest): ReviewResultDto =
        ReviewResultDto(payload.grade, 2.5, 1, 1, "2026-08-06")
}

private fun dto(id: String, status: String = "planned", est: Int = 60, order: Int = 0) = TodayTaskDto(
    id = id,
    subjectName = "科目",
    knowledgePointName = "知识点",
    title = "任务$id",
    plannedDate = "2026-08-05",
    estMinutes = est,
    status = status,
    actualMinutes = null,
    carryCount = 1,
    order = order,
)

class TodayRepositoryTest {
    @Test
    fun loadTodayCachesRemoteTasks() = runTest {
        val api = FakeApi()
        val dao = FakeDao()
        api.todayResponse = TodayDto("2026-08-05", 120, 0, 120, listOf(dto("a"), dto("b", order = 1)))
        val repository = TodayRepository(api, dao)

        val snapshot = repository.loadToday("2026-08-05")

        assertEquals(false, snapshot.fromCache)
        assertEquals(2, snapshot.tasks.size)
        assertEquals(120, snapshot.plannedMinutes)
        assertEquals(2, dao.tasksFor("2026-08-05").size)
    }

    @Test
    fun loadTodayFallsBackToCacheWhenOffline() = runTest {
        val api = FakeApi()
        val dao = FakeDao()
        api.todayResponse = TodayDto("2026-08-05", 60, 0, 60, listOf(dto("a")))
        val repository = TodayRepository(api, dao)
        repository.loadToday("2026-08-05")

        api.offline = true
        val snapshot = repository.loadToday("2026-08-05")

        assertEquals(true, snapshot.fromCache)
        assertEquals(1, snapshot.tasks.size)
        assertEquals(60, snapshot.remainingMinutes)
    }

    @Test
    fun offlineCheckInQueuesAndCompletesLocally() = runTest {
        val api = FakeApi()
        val dao = FakeDao()
        api.todayResponse = TodayDto("2026-08-05", 60, 0, 60, listOf(dto("a")))
        val repository = TodayRepository(api, dao)
        repository.loadToday("2026-08-05")

        api.offline = true
        val result = repository.checkIn("a", 50)

        assertEquals(CheckInResult.Queued, result)
        assertTrue(repository.hasPendingCheckIns())
        val snapshot = repository.loadToday("2026-08-05")
        assertEquals("completed", snapshot.tasks.single().status)
        assertEquals(50, snapshot.completedMinutes)
        assertEquals(1, snapshot.pendingCheckIns)
    }

    @Test
    fun syncReplaysQueueOnceAndClearsIt() = runTest {
        val api = FakeApi()
        val dao = FakeDao()
        api.todayResponse = TodayDto("2026-08-05", 120, 0, 120, listOf(dto("a"), dto("b", order = 1)))
        val repository = TodayRepository(api, dao)
        repository.loadToday("2026-08-05")

        api.offline = true
        repository.checkIn("a", 50)
        repository.checkIn("b", 40)

        api.offline = false
        val synced = repository.syncPendingCheckIns()

        assertEquals(2, synced)
        assertEquals(listOf("a" to 50, "b" to 40), api.completions)
        assertEquals(false, repository.hasPendingCheckIns())
        assertEquals(0, repository.syncPendingCheckIns())
    }

    @Test
    fun syncStopsOnNetworkFailureAndKeepsQueue() = runTest {
        val api = FakeApi()
        val dao = FakeDao()
        api.todayResponse = TodayDto("2026-08-05", 60, 0, 60, listOf(dto("a")))
        val repository = TodayRepository(api, dao)
        repository.loadToday("2026-08-05")

        api.offline = true
        repository.checkIn("a", 30)
        val synced = repository.syncPendingCheckIns()

        assertEquals(0, synced)
        assertTrue(repository.hasPendingCheckIns())
    }

    @Test
    fun syncDropsRejectedCheckIns() = runTest {
        val api = FakeApi()
        val dao = FakeDao()
        api.todayResponse = TodayDto("2026-08-05", 60, 0, 60, listOf(dto("a")))
        val repository = TodayRepository(api, dao)
        repository.loadToday("2026-08-05")

        api.offline = true
        repository.checkIn("a", 30)
        api.offline = false
        api.rejectWith = 404
        val synced = repository.syncPendingCheckIns()

        assertEquals(0, synced)
        assertEquals(false, repository.hasPendingCheckIns())
    }

    @Test
    fun onlineCheckInSyncsImmediately() = runTest {
        val api = FakeApi()
        val dao = FakeDao()
        api.todayResponse = TodayDto("2026-08-05", 60, 0, 60, listOf(dto("a")))
        val repository = TodayRepository(api, dao)
        repository.loadToday("2026-08-05")

        val result = repository.checkIn("a", 45)

        assertEquals(CheckInResult.Synced, result)
        assertEquals(listOf("a" to 45), api.completions)
        assertEquals(false, repository.hasPendingCheckIns())
    }
}

package com.graduateentrance.app.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction

@Dao
interface TodayDao {
    @Query("SELECT * FROM today_tasks WHERE plannedDate = :date ORDER BY taskOrder, id")
    suspend fun tasksFor(date: String): List<TodayTaskEntity>

    @Query("DELETE FROM today_tasks WHERE plannedDate = :date")
    suspend fun deleteTasksFor(date: String)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTasks(tasks: List<TodayTaskEntity>)

    @Transaction
    suspend fun replaceDay(date: String, tasks: List<TodayTaskEntity>) {
        deleteTasksFor(date)
        insertTasks(tasks)
    }

    @Query("UPDATE today_tasks SET status = 'completed', actualMinutes = :actualMinutes WHERE id = :taskId")
    suspend fun markCompleted(taskId: String, actualMinutes: Int)

    @Query("SELECT * FROM pending_check_ins ORDER BY queuedAt, taskId")
    suspend fun pendingCheckIns(): List<PendingCheckInEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun enqueueCheckIn(checkIn: PendingCheckInEntity)

    @Query("DELETE FROM pending_check_ins WHERE taskId = :taskId")
    suspend fun removeCheckIn(taskId: String)
}

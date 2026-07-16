package com.graduateentrance.app.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "today_tasks")
data class TodayTaskEntity(
    @PrimaryKey val id: String,
    val plannedDate: String,
    val subjectName: String,
    val knowledgePointName: String,
    val title: String,
    val estMinutes: Int,
    val status: String,
    val actualMinutes: Int?,
    val carryCount: Int,
    val taskOrder: Int,
)

@Entity(tableName = "pending_check_ins")
data class PendingCheckInEntity(
    @PrimaryKey val taskId: String,
    val actualMinutes: Int,
    val queuedAt: Long,
)

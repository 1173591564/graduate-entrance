package com.graduateentrance.app.network

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

data class ServiceStatus(
    val status: String,
    val service: String,
    val environment: String,
)

data class TodayTaskDto(
    val id: String,
    @SerializedName("subject_name") val subjectName: String,
    @SerializedName("knowledge_point_name") val knowledgePointName: String,
    val title: String,
    @SerializedName("planned_date") val plannedDate: String,
    @SerializedName("est_minutes") val estMinutes: Int,
    val status: String,
    @SerializedName("actual_minutes") val actualMinutes: Int?,
    @SerializedName("carry_count") val carryCount: Int,
    @SerializedName("order") val order: Int,
)

data class TodayDto(
    val date: String,
    @SerializedName("planned_minutes") val plannedMinutes: Int,
    @SerializedName("completed_minutes") val completedMinutes: Int,
    @SerializedName("remaining_minutes") val remainingMinutes: Int,
    val tasks: List<TodayTaskDto>,
)

data class TaskCompletionRequest(
    @SerializedName("actual_minutes") val actualMinutes: Int,
)

interface GraduateEntranceApi {
    @GET("api/ping")
    suspend fun ping(): ServiceStatus

    @GET("api/today")
    suspend fun today(@Query("date") date: String): TodayDto

    @POST("api/tasks/{taskId}/done")
    suspend fun completeTask(
        @Path("taskId") taskId: String,
        @Body payload: TaskCompletionRequest,
    ): TodayTaskDto
}

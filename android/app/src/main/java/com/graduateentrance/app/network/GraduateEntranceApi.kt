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

data class ProblemKnowledgePointDto(
    @SerializedName("knowledge_point_id") val knowledgePointId: String,
    @SerializedName("knowledge_point_name") val knowledgePointName: String,
    val role: String,
    val weight: Double,
)

data class SolutionDto(
    val id: String,
    @SerializedName("content_md") val contentMd: String,
    @SerializedName("method_tag") val methodTag: String,
    val source: String,
    val verified: Boolean,
)

data class ReviewProblemDto(
    val id: String,
    @SerializedName("subject_name") val subjectName: String?,
    @SerializedName("content_md") val contentMd: String,
    val kind: String,
    val status: String,
    @SerializedName("due_date") val dueDate: String?,
    val reps: Int,
    @SerializedName("knowledge_points") val knowledgePoints: List<ProblemKnowledgePointDto>,
    val solutions: List<SolutionDto>,
)

data class DueReviewsDto(
    val total: Int,
    @SerializedName("as_of") val asOf: String,
    val problems: List<ReviewProblemDto>,
)

data class ReviewRequest(
    val grade: String,
)

data class ReviewResultDto(
    val grade: String,
    val ef: Double,
    @SerializedName("interval_days") val intervalDays: Int,
    val reps: Int,
    @SerializedName("due_date") val dueDate: String,
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

    @GET("api/problems/reviews/due")
    suspend fun dueReviews(
        @Query("include_drafts") includeDrafts: Boolean,
        @Query("limit") limit: Int,
    ): DueReviewsDto

    @POST("api/problems/{problemId}/review")
    suspend fun reviewProblem(
        @Path("problemId") problemId: String,
        @Body payload: ReviewRequest,
    ): ReviewResultDto
}

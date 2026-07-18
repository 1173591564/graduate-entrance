package com.graduateentrance.app.network

import com.google.gson.annotations.SerializedName
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Streaming

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
    @SerializedName("study_module") val studyModule: String? = null,
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

data class TaskUpdateRequest(
    @SerializedName("est_minutes") val estMinutes: Int,
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

data class ProblemCreatedDto(
    val id: String,
    val status: String,
    val images: List<String>,
)

data class ExtractedKnowledgePointDto(
    @SerializedName("knowledge_point_id") val knowledgePointId: String,
    @SerializedName("knowledge_point_name") val knowledgePointName: String,
    val role: String,
    val weight: Double,
)

data class ExtractedSolutionDto(
    @SerializedName("content_md") val contentMd: String,
    @SerializedName("method_tag") val methodTag: String,
)

data class ExtractionResultDto(
    @SerializedName("problem_id") val problemId: String,
    val model: String,
    @SerializedName("content_md") val contentMd: String,
    @SerializedName("knowledge_points") val knowledgePoints: List<ExtractedKnowledgePointDto>,
    val solution: ExtractedSolutionDto?,
)

data class ReviewResultDto(
    val grade: String,
    val ef: Double,
    @SerializedName("interval_days") val intervalDays: Int,
    val reps: Int,
    @SerializedName("due_date") val dueDate: String,
)

data class PaperDto(
    val id: String,
    @SerializedName("rel_path") val relPath: String,
    val title: String,
    val category: String,
    @SerializedName("size_bytes") val sizeBytes: Long,
    val status: String,
    @SerializedName("has_file") val hasFile: Boolean,
    @SerializedName("started_on") val startedOn: String?,
    @SerializedName("finished_on") val finishedOn: String?,
)

data class PaperStatsDto(
    @SerializedName("total_count") val totalCount: Int,
    @SerializedName("unread_count") val unreadCount: Int,
    @SerializedName("reading_count") val readingCount: Int,
    @SerializedName("done_count") val doneCount: Int,
)

data class PaperGroupDto(
    val category: String,
    val papers: List<PaperDto>,
)

data class PaperListDto(
    val groups: List<PaperGroupDto>,
    val stats: PaperStatsDto,
)

data class PaperTodayDto(
    val date: String,
    val paper: PaperDto?,
    val stats: PaperStatsDto,
)

data class PaperStatusRequest(
    val status: String,
)

data class PaperStatusResultDto(
    val paper: PaperDto,
)

data class RecitationItemDto(
    val id: String,
    val subject: String,
    val category: String,
    val title: String,
    @SerializedName("content_md") val contentMd: String,
    @SerializedName("recite_count") val reciteCount: Int,
    @SerializedName("last_recited_on") val lastRecitedOn: String?,
    @SerializedName("recited_today") val recitedToday: Boolean,
)

data class RecitationStatsDto(
    @SerializedName("total_count") val totalCount: Int,
    @SerializedName("recited_today") val recitedToday: Int,
    @SerializedName("never_recited") val neverRecited: Int,
)

data class RecitationGroupDto(
    val category: String,
    val items: List<RecitationItemDto>,
)

data class RecitationListDto(
    val groups: List<RecitationGroupDto>,
    val stats: RecitationStatsDto,
)

data class RecitationTodayDto(
    val date: String,
    val item: RecitationItemDto?,
    val stats: RecitationStatsDto,
)

data class ReciteRequest(
    val undo: Boolean = false,
)

data class ReciteResultDto(
    val item: RecitationItemDto,
)

data class VocabWordDto(
    val id: String,
    val word: String,
    val meaning: String,
    val phonetic: String,
    @SerializedName("example_en") val exampleEn: String,
    @SerializedName("example_zh") val exampleZh: String,
    @SerializedName("book_page") val bookPage: Int,
    val ef: Double,
    @SerializedName("interval_days") val intervalDays: Int,
    @SerializedName("due_date") val dueDate: String?,
    val reps: Int,
)

data class VocabTodayDto(
    val date: String,
    @SerializedName("due_words") val dueWords: List<VocabWordDto>,
    @SerializedName("new_words") val newWords: List<VocabWordDto>,
    @SerializedName("due_count") val dueCount: Int,
    @SerializedName("learned_count") val learnedCount: Int,
    @SerializedName("total_count") val totalCount: Int,
    @SerializedName("reviewed_today_count") val reviewedTodayCount: Int,
)

data class VocabGradeRequest(
    val grade: String,
)

data class VocabGradeResultDto(
    val word: VocabWordDto,
    val grade: String,
    @SerializedName("due_date") val dueDate: String,
)

data class VocabDictationDto(
    val date: String,
    val words: List<VocabWordDto>,
)

data class VocabStatsDto(
    @SerializedName("total_count") val totalCount: Int,
    @SerializedName("learned_count") val learnedCount: Int,
    @SerializedName("due_count") val dueCount: Int,
    @SerializedName("mastered_count") val masteredCount: Int,
)

data class ChatConversationDto(
    val id: String,
    val title: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String,
)

data class ChatConversationListDto(
    val total: Int,
    val conversations: List<ChatConversationDto>,
)

data class ChatStepDto(
    val type: String,
    val content: String,
)

data class ChatMessageDto(
    val id: String,
    @SerializedName("conversation_id") val conversationId: String,
    val role: String,
    @SerializedName("content_md") val contentMd: String,
    val images: List<String>,
    val steps: List<ChatStepDto> = emptyList(),
    @SerializedName("created_at") val createdAt: String,
)

data class ChatHistoryDto(
    val conversation: ChatConversationDto,
    val messages: List<ChatMessageDto>,
)

data class ChatSendResultDto(
    val conversation: ChatConversationDto,
    @SerializedName("user_message") val userMessage: ChatMessageDto,
    val reply: ChatMessageDto,
    val model: String,
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

    @PATCH("api/tasks/{taskId}")
    suspend fun updateTask(
        @Path("taskId") taskId: String,
        @Body payload: TaskUpdateRequest,
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

    @Multipart
    @POST("api/problems")
    suspend fun submitProblem(
        @Part("kind") kind: RequestBody,
        @Part("note") note: RequestBody,
        @Part images: List<MultipartBody.Part>,
    ): ProblemCreatedDto

    @POST("api/problems/{problemId}/extract")
    suspend fun extractProblem(@Path("problemId") problemId: String): ExtractionResultDto

    @GET("api/papers")
    suspend fun papers(): PaperListDto

    @GET("api/papers/today")
    suspend fun papersToday(): PaperTodayDto

    @POST("api/papers/{paperId}/status")
    suspend fun setPaperStatus(
        @Path("paperId") paperId: String,
        @Body payload: PaperStatusRequest,
    ): PaperStatusResultDto

    @Streaming
    @GET("api/papers/{paperId}/file")
    suspend fun downloadPaper(@Path("paperId") paperId: String): ResponseBody

    @GET("api/recitations")
    suspend fun recitations(@Query("subject") subject: String?): RecitationListDto

    @GET("api/recitations/today")
    suspend fun recitationToday(@Query("subject") subject: String?): RecitationTodayDto

    @POST("api/recitations/{itemId}/recite")
    suspend fun reciteItem(
        @Path("itemId") itemId: String,
        @Body payload: ReciteRequest,
    ): ReciteResultDto

    @GET("api/vocab/today")
    suspend fun vocabToday(
        @Query("new_limit") newLimit: Int,
    ): VocabTodayDto

    @POST("api/vocab/{wordId}/grade")
    suspend fun gradeVocabWord(
        @Path("wordId") wordId: String,
        @Body payload: VocabGradeRequest,
    ): VocabGradeResultDto

    @GET("api/vocab/dictation")
    suspend fun vocabDictation(): VocabDictationDto

    @POST("api/vocab/{wordId}/enrich")
    suspend fun enrichVocabWord(
        @Path("wordId") wordId: String,
    ): VocabWordDto

    @GET("api/vocab/stats")
    suspend fun vocabStats(): VocabStatsDto

    @GET("api/chat/conversations")
    suspend fun chatConversations(): ChatConversationListDto

    @GET("api/chat/conversations/{conversationId}")
    suspend fun chatHistory(
        @Path("conversationId") conversationId: String,
    ): ChatHistoryDto

    @DELETE("api/chat/conversations/{conversationId}")
    suspend fun deleteChatConversation(
        @Path("conversationId") conversationId: String,
    ): Response<Unit>

    @Multipart
    @POST("api/chat/messages")
    suspend fun sendChatMessage(
        @Part("conversation_id") conversationId: RequestBody?,
        @Part("content") content: RequestBody,
        @Part images: List<MultipartBody.Part>,
    ): ChatSendResultDto
}

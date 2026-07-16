package com.graduateentrance.app.data

import com.graduateentrance.app.network.GraduateEntranceApi
import com.graduateentrance.app.network.ReviewProblemDto
import com.graduateentrance.app.network.ReviewRequest
import com.graduateentrance.app.network.ReviewResultDto
import java.io.IOException
import retrofit2.HttpException

sealed interface ReviewsLoadResult {
    data class Loaded(val asOf: String, val total: Int, val problems: List<ReviewProblemDto>) :
        ReviewsLoadResult
    data object Offline : ReviewsLoadResult
    data class Rejected(val code: Int) : ReviewsLoadResult
}

sealed interface GradeResult {
    data class Graded(val result: ReviewResultDto) : GradeResult
    data object Offline : GradeResult
    data class Rejected(val code: Int) : GradeResult
}

class ReviewsRepository(private val api: GraduateEntranceApi) {
    suspend fun loadDueReviews(includeDrafts: Boolean, limit: Int = 50): ReviewsLoadResult =
        try {
            val response = api.dueReviews(includeDrafts, limit)
            ReviewsLoadResult.Loaded(response.asOf, response.total, response.problems)
        } catch (_: IOException) {
            ReviewsLoadResult.Offline
        } catch (error: HttpException) {
            ReviewsLoadResult.Rejected(error.code())
        }

    suspend fun grade(problemId: String, grade: String): GradeResult =
        try {
            GradeResult.Graded(api.reviewProblem(problemId, ReviewRequest(grade)))
        } catch (_: IOException) {
            GradeResult.Offline
        } catch (error: HttpException) {
            GradeResult.Rejected(error.code())
        }
}

package com.graduateentrance.app.data

import com.graduateentrance.app.network.GraduateEntranceApi
import com.graduateentrance.app.network.ProblemCreatedDto
import java.io.IOException
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.HttpException

data class CaptureImage(
    val bytes: ByteArray,
    val mimeType: String,
)

sealed interface CaptureResult {
    data class Created(val problem: ProblemCreatedDto) : CaptureResult
    data object Offline : CaptureResult
    data class Rejected(val code: Int) : CaptureResult
}

private val IMAGE_EXTENSIONS = mapOf(
    "image/jpeg" to "jpg",
    "image/png" to "png",
    "image/webp" to "webp",
)

class CaptureRepository(private val api: GraduateEntranceApi) {
    suspend fun submitProblem(
        kind: String,
        note: String,
        images: List<CaptureImage>,
    ): CaptureResult =
        try {
            val parts = images.mapIndexed { index, image ->
                val extension = IMAGE_EXTENSIONS[image.mimeType] ?: "jpg"
                MultipartBody.Part.createFormData(
                    "images",
                    "capture-$index.$extension",
                    image.bytes.toRequestBody(image.mimeType.toMediaType()),
                )
            }
            val created = api.submitProblem(
                kind = kind.toRequestBody("text/plain".toMediaType()),
                note = note.toRequestBody("text/plain".toMediaType()),
                images = parts,
            )
            CaptureResult.Created(created)
        } catch (_: IOException) {
            CaptureResult.Offline
        } catch (error: HttpException) {
            CaptureResult.Rejected(error.code())
        }
}

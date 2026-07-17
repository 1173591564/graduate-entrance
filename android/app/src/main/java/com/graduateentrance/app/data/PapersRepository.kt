package com.graduateentrance.app.data

import com.graduateentrance.app.network.GraduateEntranceApi
import com.graduateentrance.app.network.PaperDto
import com.graduateentrance.app.network.PaperGroupDto
import com.graduateentrance.app.network.PaperStatsDto
import com.graduateentrance.app.network.PaperStatusRequest
import java.io.File
import java.io.IOException
import retrofit2.HttpException

sealed interface PapersLoadResult {
    data class Loaded(
        val today: PaperDto?,
        val groups: List<PaperGroupDto>,
        val stats: PaperStatsDto,
    ) : PapersLoadResult
    data object Offline : PapersLoadResult
    data class Rejected(val code: Int) : PapersLoadResult
}

sealed interface PaperStatusResult {
    data class Updated(val paper: PaperDto) : PaperStatusResult
    data object Offline : PaperStatusResult
    data class Rejected(val code: Int) : PaperStatusResult
}

sealed interface PaperDownloadResult {
    data class Ready(val file: File) : PaperDownloadResult
    data object Offline : PaperDownloadResult
    data class Rejected(val code: Int) : PaperDownloadResult
}

class PapersRepository(private val api: GraduateEntranceApi) {
    suspend fun load(): PapersLoadResult =
        try {
            val today = api.papersToday()
            val list = api.papers()
            PapersLoadResult.Loaded(today.paper, list.groups, list.stats)
        } catch (_: IOException) {
            PapersLoadResult.Offline
        } catch (error: HttpException) {
            PapersLoadResult.Rejected(error.code())
        }

    suspend fun setStatus(paperId: String, status: String): PaperStatusResult =
        try {
            PaperStatusResult.Updated(
                api.setPaperStatus(paperId, PaperStatusRequest(status)).paper,
            )
        } catch (_: IOException) {
            PaperStatusResult.Offline
        } catch (error: HttpException) {
            PaperStatusResult.Rejected(error.code())
        }

    suspend fun download(paperId: String, target: File): PaperDownloadResult =
        try {
            api.downloadPaper(paperId).use { body ->
                target.parentFile?.mkdirs()
                body.byteStream().use { input ->
                    target.outputStream().use { output -> input.copyTo(output) }
                }
            }
            PaperDownloadResult.Ready(target)
        } catch (_: IOException) {
            PaperDownloadResult.Offline
        } catch (error: HttpException) {
            PaperDownloadResult.Rejected(error.code())
        }
}

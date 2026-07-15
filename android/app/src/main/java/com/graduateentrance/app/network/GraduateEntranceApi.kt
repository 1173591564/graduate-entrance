package com.graduateentrance.app.network

import retrofit2.http.GET

data class ServiceStatus(
    val status: String,
    val service: String,
    val environment: String,
)

interface GraduateEntranceApi {
    @GET("api/ping")
    suspend fun ping(): ServiceStatus
}

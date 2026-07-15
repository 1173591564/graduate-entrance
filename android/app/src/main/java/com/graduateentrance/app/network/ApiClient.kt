package com.graduateentrance.app.network

import com.graduateentrance.app.BuildConfig
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    private val httpClient = OkHttpClient.Builder()
        .addInterceptor { chain ->
            val request = chain.request()
                .newBuilder()
                .header("Authorization", "Bearer ${BuildConfig.API_TOKEN}")
                .build()
            chain.proceed(request)
        }
        .build()

    val service: GraduateEntranceApi = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(httpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(GraduateEntranceApi::class.java)
}

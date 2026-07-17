package com.graduateentrance.app.network

import com.graduateentrance.app.BuildConfig
import com.graduateentrance.app.data.AppSettings
import java.time.Duration
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(Duration.ofSeconds(15))
        .readTimeout(Duration.ofSeconds(180))
        .writeTimeout(Duration.ofSeconds(60))
        .addInterceptor { chain ->
            val original = chain.request()
            val builder = original.newBuilder()
                .header("Authorization", "Bearer ${AppSettings.token}")
            val base = AppSettings.baseUrl.toHttpUrlOrNull()
            if (base != null) {
                builder.url(
                    original.url.newBuilder()
                        .scheme(base.scheme)
                        .host(base.host)
                        .port(base.port)
                        .build(),
                )
            }
            chain.proceed(builder.build())
        }
        .build()

    val service: GraduateEntranceApi = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(httpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(GraduateEntranceApi::class.java)
}

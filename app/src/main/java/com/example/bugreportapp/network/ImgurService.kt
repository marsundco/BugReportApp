package com.example.bugreportapp.network

import retrofit2.http.Headers
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.Call
import okhttp3.MultipartBody

interface ImgurService {

    @Headers("Authorization: Client-ID 1bf4e65fb619200")
    @Multipart
    @POST("upload")
    fun uploadImage(@Part image: MultipartBody.Part): Call<ImgurResponse>
}

data class ImgurResponse(
    val data: ImgurData,
    val success: Boolean,
    val status: Int
)

data class ImgurData(
    val link: String
)

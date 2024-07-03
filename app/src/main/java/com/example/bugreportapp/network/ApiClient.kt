package com.example.bugreportapp.network

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {

    private const val GOODDAY_BASE_URL = "https://api.goodday.work/"

    //private const val IMGUR_CLIENT_ID = "YOUR_IMGUR_CLIENT_ID"
    private const val IMGUR_BASE_URL = "https://api.imgur.com/3/"

    val goodDayService: GoodDayService = Retrofit.Builder()
        .baseUrl(GOODDAY_BASE_URL)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(GoodDayService::class.java)

    val imgurService: ImgurService = Retrofit.Builder()
        .baseUrl(IMGUR_BASE_URL)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(ImgurService::class.java)
}
package com.example.bugreportapp.network

import okhttp3.ResponseBody
import org.json.JSONObject
import retrofit2.Call
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.Headers
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path


interface GoodDayService {
    @Headers("Content-Type: application/json")
    @POST("/2.0/tasks")
    suspend fun createTask(@Header("gd-api-token") token: String, @Body taskData: TaskData): Response<TaskResponse>

    @Headers("Content-Type: application/json")
    @PUT("/2.0/task/{taskId}/custom-fields")
    suspend fun updateCustomFields(
        @Header("gd-api-token") token: String,
        @Path("taskId") taskId: String,
        @Body customFields: CustomFieldsData
    ): Response<ResponseBody>
}

data class TaskData(
    val projectId: String,
    val title: String,
    val fromUserId: String,
    val message: String
)

data class TaskResponse(
    val id: String,
    val shortId: String,
    // Add other fields as needed
)

data class CustomFieldsData(
    val customFields: List<CustomField>
)

data class CustomField(
    val id: String,
    val value: Any
)

data class CustomFieldsResponse(
    val success: Boolean,
    val message: String
)
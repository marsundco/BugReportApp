package com.example.bugreportapp

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.util.Log
import android.view.inputmethod.InputMethodManager
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import androidx.lifecycle.lifecycleScope
import com.example.bugreportapp.network.*
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.File
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.*
import com.google.gson.JsonParser
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.asRequestBody
import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.view.View
import android.widget.ImageView
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import com.example.bugreportapp.network.ApiClient
import com.example.bugreportapp.network.GoodDayService
import com.example.bugreportapp.network.ImgurService



class MainActivity : AppCompatActivity() {

    private lateinit var shortDescEditText: EditText
    private lateinit var projectNameEditText: EditText
    private lateinit var productIdEditText: EditText
    private lateinit var detailedDescEditText: EditText
    private lateinit var reporterNameEditText: EditText
    private lateinit var submitButton: Button
    private lateinit var takePhotoButton: Button
    private lateinit var imageView: ImageView

    private val goodDayService: GoodDayService = ApiClient.goodDayService
    private val imgurService: ImgurService = ApiClient.imgurService

    private lateinit var photoUri: Uri

    private val requestCameraPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            dispatchTakePictureIntent()
        } else {
            Toast.makeText(this, "Camera permission is required to take photos", Toast.LENGTH_SHORT).show()
        }
    }

    private fun dispatchTakePictureIntent() {
        // Create the camera_intent ACTION_IMAGE_CAPTURE it will open the camera for capture the image
        val cameraIntent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        // Start the activity with camera_intent, and request pic id
        startActivityForResult(cameraIntent, PIC_ID)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        shortDescEditText = findViewById(R.id.shortDescEditText)
        projectNameEditText = findViewById(R.id.projectNameEditText)
        productIdEditText = findViewById(R.id.productIdEditText)
        detailedDescEditText = findViewById(R.id.detailedDescEditText)
        reporterNameEditText = findViewById(R.id.reporterNameEditText)
        submitButton = findViewById(R.id.submitButton)
        takePhotoButton = findViewById(R.id.takePhotoButton)
        imageView = findViewById(R.id.imageView)

        takePhotoButton.setOnClickListener(View.OnClickListener {
            requestCameraPermission()
        })

//        submitButton.setOnClickListener {
//            submitReport()
//        }
    }

    // This method will help to retrieve the image
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        // Match the request 'pic id with requestCode
        if (requestCode == PIC_ID) {
            // BitMap is data structure of image file which store the image in memory
            val photo = data!!.extras!!["data"] as Bitmap?
            // Set the image in imageview for display
            imageView.setImageBitmap(photo)
        }
    }
    companion object {
        // Define the pic id
        private const val PIC_ID = 123
    }

    private fun requestCameraPermission() {
        when {
            ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED -> {
                dispatchTakePictureIntent()
            }
            shouldShowRequestPermissionRationale(Manifest.permission.CAMERA) -> {
                Toast.makeText(this, "Camera permission is required to take photos", Toast.LENGTH_SHORT).show()
            }
            else -> {
                requestCameraPermissionLauncher.launch(Manifest.permission.CAMERA)
            }
        }
    }

    private fun createImageFile(): File {
        val storageDir: File = getExternalFilesDir(Environment.DIRECTORY_PICTURES)!!
        return File.createTempFile(
            "JPEG_${System.currentTimeMillis()}_",
            ".jpg",
            storageDir
        )
    }

//    private fun submitReport() {
//        val shortDesc = shortDescEditText.text.toString()
//        val projectName = projectNameEditText.text.toString()
//        val productId = productIdEditText.text.toString()
//        val detailedDesc = detailedDescEditText.text.toString()
//        val reporterName = reporterNameEditText.text.toString()
//
//        val message = detailedDesc
//
//        if (shortDesc.isEmpty()) {
//            Toast.makeText(this, "Short description cannot be empty", Toast.LENGTH_SHORT).show()
//            return
//        }
//
//        // Launch a coroutine to call the suspend function
//        lifecycleScope.launch {
//            try {
//                val imgurLinks = uploadImagesToImgur()
//                val response = createTask(
//                    "SnVrYd", // Replace with your project ID
//                    shortDesc,
//                    "USER1-ID", // Replace with actual user ID
//                    message + "\n" + imgurLinks.joinToString("\n"),
//                    projectName,
//                    productId,
//                    reporterName
//                )
//                // Handle the response if needed
//                Toast.makeText(this@MainActivity, "Task created successfully", Toast.LENGTH_SHORT).show()
//            } catch (e: Exception) {
//                // Handle the exception
//                Toast.makeText(this@MainActivity, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
//            }
//            clearInputs()
//        }
//    }

//    private suspend fun uploadImagesToImgur(photoUri: Uri): List<String> {
//        val imgurLinks = mutableListOf<String>()
//        withContext(Dispatchers.IO) {
//            val file = File(photoUri.path!!)
//            val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
//            val body = MultipartBody.Part.createFormData("image", file.name, requestFile)
//
//            val response = imgurService.uploadImage(body).execute()
//
//            if (response.isSuccessful) {
//                val responseBody = response.body()?.string()
//                if (responseBody != null) {
//                    val jsonElement = JsonParser.parseString(responseBody)
//                    val link = jsonElement.asJsonObject
//                        .getAsJsonObject("data")
//                        ?.get("link")?.asString
//                    if (link != null) {
//                        imgurLinks.add(link)
//                    }
//                }
//            } else {
//                Log.e("ImgurService", "Error uploading image: ${response.code()}")
//            }
//        }
//        return imgurLinks
//    }



    private suspend fun createTask(
        projectId: String,
        title: String,
        fromUserId: String,
        message: String,
        projectName: String,
        productId: String,
        reporterName: String
    ): TaskResponse {
        val taskData = TaskData(
            projectId = projectId,
            title = title,
            fromUserId = fromUserId,
            message = message
        )

        // Create task
        val tokenGoodDay = "a15e14026c0541e39fe1c04587ca11bc"
        val response = goodDayService.createTask(tokenGoodDay, taskData)
        if (!response.isSuccessful) throw IOException("Unexpected code ${response.code()}")

        val newTask = response.body() ?: throw IOException("Empty response body")

        // Update custom fields
        val taskId = newTask.id
        val customFields = CustomFieldsData(
            customFields = listOf(
                CustomField(id = "l8dmpO", value = projectName),
                CustomField(id = "MBYlLP", value = productId),
                CustomField(id = "5Mk38y", value = reporterName)
                // CustomField(id = "I9vbkT", value = departmentNo)
            )
        )

        val customFieldsResponse =
            goodDayService.updateCustomFields(tokenGoodDay, taskId, customFields)
        if (!customFieldsResponse.isSuccessful) {
            Log.e("GoodDayService", "Error updating custom fields: ${customFieldsResponse.code()}")
            throw IOException("Unexpected code ${customFieldsResponse.code()}")
        }

        val customFieldsResponseBody = customFieldsResponse.body()?.string()
        Log.d("GoodDayService", "Update Custom Fields Response Body: $customFieldsResponseBody")

        // Check if the response is a string and handle it
        if (customFieldsResponseBody != null && customFieldsResponseBody.startsWith("{")) {
            // Parse JSON response if it's an object
            val customFieldsResponseObject =
                Gson().fromJson(customFieldsResponseBody, CustomFieldsResponse::class.java)
            Log.d("GoodDayService", "Custom Fields Response: $customFieldsResponseObject")
        } else {
            // Handle raw string response
            Log.d("GoodDayService", "Custom Fields Response is not a JSON object")
        }

        return newTask
    }

    private fun clearInputs() {
        shortDescEditText.text.clear()
        projectNameEditText.text.clear()
        productIdEditText.text.clear()
        detailedDescEditText.text.clear()
        reporterNameEditText.text.clear()

        // Hide the keyboard
        val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
        var view = currentFocus
        if (view == null) {
            view = EditText(this) // create a new EditText to ensure it's not null
        }
        imm.hideSoftInputFromWindow(view.windowToken, 0)
    }
}

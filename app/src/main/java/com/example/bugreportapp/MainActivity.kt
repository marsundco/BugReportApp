package com.example.bugreportapp

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.view.View
import android.view.inputmethod.InputMethodManager
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import com.example.bugreportapp.network.*
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.*


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

    private lateinit var photo: File

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
        photo = createNewImageFile(this)
        val uri = FileProvider.getUriForFile(this, "$packageName.provider", photo)
        cameraIntent.putExtra(MediaStore.EXTRA_OUTPUT, uri)
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
        if (resultCode != RESULT_OK){
            return
        }
        // Match the request 'pic id with requestCode
        if (requestCode == PIC_ID) {
            val resultBitmap : Bitmap = BitmapFactory.decodeFile(photo.absolutePath)
            saveBitmapToFile(resultBitmap, "image/jpg", photo.absolutePath)
            imageView.setImageBitmap(resultBitmap)
        }
    }

    private fun saveBitmapToFile(bitmap: Bitmap?, mimeType: String, absolutePath: String?) {
        if (absolutePath == null || bitmap == null){
            return
        }

        val file = File(absolutePath)
        val stream = FileOutputStream(file)

        if (mimeType.contains("jpg", true) || mimeType.contains("jpeg", true))
            bitmap.compress(Bitmap.CompressFormat.JPEG, 100, stream)
        else if (mimeType.contains("png", true))
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)

        stream.close()
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

    @Throws(IOException::class)
    fun createNewImageFile(context: Context): File {
        // Create an image file name
        val timeStamp: String = SimpleDateFormat("yyyyMMdd_HHmmss").format(Date())
        val storageDir: File? = context.getExternalFilesDir(Environment.DIRECTORY_PICTURES)
        return File.createTempFile(
            "JPEG_${timeStamp}_", /* prefix */
            ".jpg", /* suffix */
            storageDir /* directory */
        ).apply {
            // Save a file: path for use with ACTION_VIEW intents
            absolutePath
        }
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

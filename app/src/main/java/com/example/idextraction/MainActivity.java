package com.example.idextraction;

import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageCapture;
import androidx.camera.core.ImageCaptureException;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.google.common.util.concurrent.ListenableFuture;

import org.json.JSONObject;

import java.io.File;
import java.io.IOException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

public class MainActivity extends AppCompatActivity {
    private PreviewView cameraPreviewView;
    private Button captureButton;
    private TextView resultTextView;
    private ExecutorService cameraExecutor;
    private ImageCapture imageCapture;
    private static final int REQUEST_CODE_PERMISSIONS = 10;
    private static final String[] REQUIRED_PERMISSIONS = new String[]{
            Manifest.permission.CAMERA
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        cameraPreviewView = findViewById(R.id.cameraPreviewView);
        captureButton = findViewById(R.id.captureButton);
        resultTextView = findViewById(R.id.resultTextView);

        if (allPermissionsGranted()) {
            startCamera();
        } else {
            ActivityCompat.requestPermissions(
                    this, REQUIRED_PERMISSIONS, REQUEST_CODE_PERMISSIONS);
        }

        captureButton.setOnClickListener(v -> takePhoto());
        cameraExecutor = Executors.newSingleThreadExecutor();
    }

    private void takePhoto() {
        if (imageCapture == null) {
            Toast.makeText(this, "Camera not initialized", Toast.LENGTH_SHORT).show();
            return;
        }

        File photoFile = new File(getExternalFilesDir(null), "id_card.jpg");
        ImageCapture.OutputFileOptions outputOptions =
                new ImageCapture.OutputFileOptions.Builder(photoFile).build();

        imageCapture.takePicture(outputOptions, cameraExecutor,
                new ImageCapture.OnImageSavedCallback() {
                    @Override
                    public void onImageSaved(@NonNull ImageCapture.OutputFileResults output) {
                        if (!photoFile.exists() || photoFile.length() == 0) {
                            Toast.makeText(MainActivity.this, "Photo file is empty or not found", Toast.LENGTH_SHORT).show();
                            return;
                        }
                        uploadImage(photoFile);
                    }

                    @Override
                    public void onError(@NonNull ImageCaptureException exception) {
                        runOnUiThread(() -> {
                            Toast.makeText(MainActivity.this,
                                    "Photo capture failed: " + exception.getMessage(),
                                    Toast.LENGTH_SHORT).show();
                        });
                    }
                });
    }

    private void uploadImage(File imageFile) {
        OkHttpClient client = new OkHttpClient();

        RequestBody requestBody = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", imageFile.getName(),
                        RequestBody.create(imageFile, MediaType.parse("image/jpeg")))
                .build();

        Request request = new Request.Builder()
                .url("http://192.168.1.7:5000/upload")

                .post(requestBody)
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onResponse(@NonNull Call call, @NonNull Response response) {
                try {
                    if (response.isSuccessful() && response.body() != null) {
                        final String responseBody = response.body().string();
                        runOnUiThread(() -> {
                            try {
                                JSONObject jsonResponse = new JSONObject(responseBody);
                                updateUIWithIDCardInfo(jsonResponse);
                            } catch (Exception e) {
                                resultTextView.setText("Error parsing response: " + e.getMessage());
                            }
                        });
                    } else {
                        final String errorBody = response.body() != null ? response.body().string() : "No response body";
                        runOnUiThread(() -> {
                            resultTextView.setText("Upload failed: " + response.message() + " - " + errorBody);
                        });
                    }
                } catch (IOException e) {
                    runOnUiThread(() -> {
                        resultTextView.setText("IO Error: " + e.getMessage());
                    });
                }
            }

            @Override
            public void onFailure(@NonNull Call call, @NonNull IOException e) {
                runOnUiThread(() -> {
                    resultTextView.setText("Network Error: " + e.getMessage());
                });
            }
        });
    }

    private void updateUIWithIDCardInfo(JSONObject idCardInfo) throws Exception {
        // Fill the fields with data from the response
        EditText firstNameEditText = findViewById(R.id.firstNameEditText);
        EditText lastNameEditText = findViewById(R.id.lastNameEditText);
        EditText dateOfBirthEditText = findViewById(R.id.dateOfBirthEditText);
        EditText placeOfBirthEditText = findViewById(R.id.placeOfBirthEditText);
        EditText idCodeEditText = findViewById(R.id.idCodeEditText);

        // Set the values extracted from the ID scan
        firstNameEditText.setText(idCardInfo.getString("first_name"));
        lastNameEditText.setText(idCardInfo.getString("last_name"));
        dateOfBirthEditText.setText(idCardInfo.getString("date_of_birth"));
        placeOfBirthEditText.setText(idCardInfo.getString("place_of_birth"));
        idCodeEditText.setText(idCardInfo.getString("id_code"));
    }


    private void startCamera() {
        ListenableFuture<ProcessCameraProvider> cameraProviderFuture =
                ProcessCameraProvider.getInstance(this);

        cameraProviderFuture.addListener(() -> {
            try {
                ProcessCameraProvider cameraProvider = cameraProviderFuture.get();

                // Setup preview use case
                Preview preview = new Preview.Builder().build();
                preview.setSurfaceProvider(cameraPreviewView.getSurfaceProvider());

                // Setup image capture use case
                imageCapture = new ImageCapture.Builder()
                        .setTargetResolution(new android.util.Size(1280, 720))
                        .build();

                // Select back camera as a default
                CameraSelector cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA;

                // Unbind use cases before rebinding
                cameraProvider.unbindAll();

                // Bind use cases to camera
                cameraProvider.bindToLifecycle(
                        this, cameraSelector, preview, imageCapture);

            } catch (Exception e) {
                Toast.makeText(this, "Camera initialization failed", Toast.LENGTH_SHORT).show();
            }
        }, ContextCompat.getMainExecutor(this));
    }

    private boolean allPermissionsGranted() {
        for (String permission : REQUIRED_PERMISSIONS) {
            if (ContextCompat.checkSelfPermission(this, permission)
                    != PackageManager.PERMISSION_GRANTED) {
                return false;
            }
        }
        return true;
    }

    @Override
    public void onRequestPermissionsResult(int requestCode,
                                           @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_CODE_PERMISSIONS) {
            if (allPermissionsGranted()) {
                startCamera();
            } else {
                Toast.makeText(this, "Permissions not granted", Toast.LENGTH_SHORT).show();
                finish();
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        cameraExecutor.shutdown();
    }
}
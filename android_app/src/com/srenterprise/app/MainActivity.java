package com.srenterprise.app;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.Toast;

public class MainActivity extends Activity implements View.OnClickListener, Runnable {
    private String mPendingDocName = "SR_Enterprise_Invoice";

    public static final String APP_URL = "https://sr-enterprise.onrender.com/";
    public static final int REQUEST_CAMERA_PERMISSION = 1001;
    public static final int FILE_CHOOSER_REQUEST_CODE = 2001;
    public static final int NATIVE_CAMERA_REQUEST_CODE = 3001;

    public WebView mWebView;
    public ProgressBar mProgressBar;
    public LinearLayout mErrorLayout;
    public Button mBtnRetry;

    public ValueCallback<Uri[]> mFilePathCallback;
    public Uri mCameraCaptureUri = null;
    public volatile String mLastCapturedBase64 = null;
    private long backPressedTime = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            getWindow().setStatusBarColor(0xFF4C0519); // Maroon 950
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            try {
                android.os.StrictMode.VmPolicy.Builder builder = new android.os.StrictMode.VmPolicy.Builder();
                android.os.StrictMode.setVmPolicy(builder.build());
            } catch (Exception e) {}
        }

        mWebView = (WebView) findViewById(R.id.webview);
        mWebView.setBackgroundColor(0xFFFAFAF9);
        mProgressBar = (ProgressBar) findViewById(R.id.progress_bar);
        mErrorLayout = (LinearLayout) findViewById(R.id.error_layout);
        mBtnRetry = (Button) findViewById(R.id.btn_retry);

        mBtnRetry.setOnClickListener(this);

        requestAppPermissions();
        setupWebView();

        if (savedInstanceState == null) {
            mWebView.loadUrl(APP_URL);
        } else {
            mWebView.restoreState(savedInstanceState);
        }
    }

    @Override
    public void onClick(View v) {
        if (v == mBtnRetry) {
            if (mErrorLayout != null) mErrorLayout.setVisibility(View.GONE);
            if (mWebView != null) {
                mWebView.setVisibility(View.VISIBLE);
                mWebView.reload();
            }
        }
    }

    private void requestAppPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{
                        Manifest.permission.CAMERA,
                        Manifest.permission.READ_EXTERNAL_STORAGE
                }, REQUEST_CAMERA_PERMISSION);
            }
        }
    }

    private void setupWebView() {
        mWebView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        WebSettings settings = mWebView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        String defaultUA = settings.getUserAgentString();
        settings.setUserAgentString(defaultUA + " SREnterpriseMobileApp/1.0");

        mWebView.addJavascriptInterface(new AppJsInterface(this), "SRNativeApp");

        mWebView.setWebViewClient(new AppWebViewClient(this));
        mWebView.setWebChromeClient(new AppWebChromeClient(this));
    }

    public void openCameraFromJs() {
        runOnUiThread(new CameraLaunchRunner(this));
    }

    public void launchNativeCamera() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{Manifest.permission.CAMERA}, REQUEST_CAMERA_PERMISSION);
                return;
            }
        }
        Intent takePictureIntent = new Intent(android.provider.MediaStore.ACTION_IMAGE_CAPTURE);
        try {
            android.content.ContentValues values = new android.content.ContentValues();
            values.put(android.provider.MediaStore.Images.Media.TITLE, "SRE_DirectCam_" + System.currentTimeMillis());
            values.put(android.provider.MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
            mCameraCaptureUri = getContentResolver().insert(
                android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values
            );
            takePictureIntent.putExtra(android.provider.MediaStore.EXTRA_OUTPUT, mCameraCaptureUri);
            takePictureIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
            startActivityForResult(takePictureIntent, NATIVE_CAMERA_REQUEST_CODE);
        } catch (Exception e) {
            Toast.makeText(this, "ক্যামেরা ওপেন করা যায়নি", Toast.LENGTH_SHORT).show();
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == NATIVE_CAMERA_REQUEST_CODE) {
            if (resultCode == RESULT_OK && mCameraCaptureUri != null) {
                try {
                    // 1. Decode bounds first to compute inSampleSize
                    android.graphics.BitmapFactory.Options boundsOptions = new android.graphics.BitmapFactory.Options();
                    boundsOptions.inJustDecodeBounds = true;
                    java.io.InputStream isBounds = getContentResolver().openInputStream(mCameraCaptureUri);
                    if (isBounds != null) {
                        android.graphics.BitmapFactory.decodeStream(isBounds, null, boundsOptions);
                        isBounds.close();
                    }

                    int origWidth = boundsOptions.outWidth;
                    int origHeight = boundsOptions.outHeight;
                    int inSampleSize = 1;
                    int maxDim = Math.max(origWidth, origHeight);
                    // Keep max dimension <= 1400px to prevent OOM and Binder IPC TransactionTooLargeException
                    while (maxDim / inSampleSize > 1400) {
                        inSampleSize *= 2;
                    }

                    // 2. Decode sampled bitmap
                    android.graphics.BitmapFactory.Options decodeOptions = new android.graphics.BitmapFactory.Options();
                    decodeOptions.inSampleSize = inSampleSize;
                    java.io.InputStream isActual = getContentResolver().openInputStream(mCameraCaptureUri);
                    android.graphics.Bitmap bmp = null;
                    if (isActual != null) {
                        bmp = android.graphics.BitmapFactory.decodeStream(isActual, null, decodeOptions);
                        isActual.close();
                    }

                    if (bmp != null) {
                        // 3. Handle EXIF orientation rotation
                        try {
                            java.io.InputStream isExif = getContentResolver().openInputStream(mCameraCaptureUri);
                            if (isExif != null) {
                                android.media.ExifInterface exif = new android.media.ExifInterface(isExif);
                                int orientation = exif.getAttributeInt(
                                    android.media.ExifInterface.TAG_ORIENTATION,
                                    android.media.ExifInterface.ORIENTATION_NORMAL
                                );
                                isExif.close();
                                int rotationAngle = 0;
                                if (orientation == android.media.ExifInterface.ORIENTATION_ROTATE_90) rotationAngle = 90;
                                else if (orientation == android.media.ExifInterface.ORIENTATION_ROTATE_180) rotationAngle = 180;
                                else if (orientation == android.media.ExifInterface.ORIENTATION_ROTATE_270) rotationAngle = 270;

                                if (rotationAngle != 0) {
                                    android.graphics.Matrix matrix = new android.graphics.Matrix();
                                    matrix.postRotate(rotationAngle);
                                    android.graphics.Bitmap rotatedBmp = android.graphics.Bitmap.createBitmap(
                                        bmp, 0, 0, bmp.getWidth(), bmp.getHeight(), matrix, true
                                    );
                                    if (rotatedBmp != bmp) {
                                        bmp.recycle();
                                        bmp = rotatedBmp;
                                    }
                                }
                            }
                        } catch (Exception ignored) {}

                        // 4. Compress to 80% JPEG
                        java.io.ByteArrayOutputStream baos = new java.io.ByteArrayOutputStream();
                        bmp.compress(android.graphics.Bitmap.CompressFormat.JPEG, 80, baos);
                        byte[] bytes = baos.toByteArray();
                        bmp.recycle();

                        String base64 = android.util.Base64.encodeToString(bytes, android.util.Base64.NO_WRAP);
                        String dataUri = "data:image/jpeg;base64," + base64;
                        mLastCapturedBase64 = dataUri;

                        final String js = "if (window.SmartScanner) { " +
                                          "  if (window.SmartScanner.onNativeCameraResult) { " +
                                          "    window.SmartScanner.onNativeCameraResult('" + dataUri + "'); " +
                                          "  } else if (window.SmartScanner.checkNativePhoto) { " +
                                          "    window.SmartScanner.checkNativePhoto(); " +
                                          "  } " +
                                          "}";
                        runOnUiThread(new JsEvalRunner(this, js));
                    }
                } catch (Exception e) {
                    Toast.makeText(this, "ছবি প্রসেস করা যায়নি", Toast.LENGTH_SHORT).show();
                }
            } else {
                if (mCameraCaptureUri != null && "content".equalsIgnoreCase(mCameraCaptureUri.getScheme())) {
                    try {
                        getContentResolver().delete(mCameraCaptureUri, null, null);
                    } catch (Exception ignored) {}
                }
            }
            mCameraCaptureUri = null;
            return;
        }
        if (requestCode == FILE_CHOOSER_REQUEST_CODE) {
            if (mFilePathCallback != null) {
                Uri[] results = null;
                if (resultCode == RESULT_OK) {
                    if (mCameraCaptureUri != null) {
                        boolean hasData = false;
                        if ("file".equalsIgnoreCase(mCameraCaptureUri.getScheme())) {
                            java.io.File f = new java.io.File(mCameraCaptureUri.getPath());
                            hasData = (f.exists() && f.length() > 0);
                        } else if ("content".equalsIgnoreCase(mCameraCaptureUri.getScheme())) {
                            try (android.database.Cursor cursor = getContentResolver().query(mCameraCaptureUri, new String[]{android.provider.OpenableColumns.SIZE}, null, null, null)) {
                                if (cursor != null && cursor.moveToFirst()) {
                                    int sizeIdx = cursor.getColumnIndex(android.provider.OpenableColumns.SIZE);
                                    if (sizeIdx != -1 && cursor.getLong(sizeIdx) > 0) {
                                        hasData = true;
                                    }
                                }
                            } catch (Exception ignored) {
                                hasData = true;
                            }
                        }
                        if (hasData) {
                            results = new Uri[]{mCameraCaptureUri};
                        }
                    }
                    if (results == null && data != null) {
                        String dataString = data.getDataString();
                        if (dataString != null) {
                            results = new Uri[]{Uri.parse(dataString)};
                        } else if (data.getClipData() != null) {
                            int count = data.getClipData().getItemCount();
                            results = new Uri[count];
                            for (int i = 0; i < count; i++) {
                                results[i] = data.getClipData().getItemAt(i).getUri();
                            }
                        } else if (data.getExtras() != null && data.getExtras().get("data") != null) {
                            android.graphics.Bitmap bmp = (android.graphics.Bitmap) data.getExtras().get("data");
                            if (bmp != null) {
                                try {
                                    java.io.File f = new java.io.File(getExternalCacheDir(), "cam_thumb_" + System.currentTimeMillis() + ".jpg");
                                    java.io.FileOutputStream fos = new java.io.FileOutputStream(f);
                                    bmp.compress(android.graphics.Bitmap.CompressFormat.JPEG, 95, fos);
                                    fos.flush();
                                    fos.close();
                                    results = new Uri[]{Uri.fromFile(f)};
                                } catch (Exception e) {}
                            }
                        }
                    }
                } else {
                    if (mCameraCaptureUri != null && "content".equalsIgnoreCase(mCameraCaptureUri.getScheme())) {
                        try {
                            getContentResolver().delete(mCameraCaptureUri, null, null);
                        } catch (Exception ignored) {}
                    }
                }
                mCameraCaptureUri = null;
                mFilePathCallback.onReceiveValue(results);
                mFilePathCallback = null;
            }
        } else {
            super.onActivityResult(requestCode, resultCode, data);
        }
    }

    @Override
    public void onBackPressed() {
        if (mWebView != null && mWebView.canGoBack()) {
            mWebView.goBack();
        } else {
            if (backPressedTime + 2000 > System.currentTimeMillis()) {
                super.onBackPressed();
            } else {
                Toast.makeText(this, "অ্যাপ বন্ধ করতে আবার ব্যাক চাপুন", Toast.LENGTH_SHORT).show();
                backPressedTime = System.currentTimeMillis();
            }
        }
    }

    public void triggerPrint(String docName) {
        this.mPendingDocName = (docName != null && !docName.isEmpty()) ? docName : "SR_Enterprise_Invoice";
        runOnUiThread(this);
    }

    @Override
    public void run() {
        printCurrentPage(this.mPendingDocName);
    }

    public void printCurrentPage(String docName) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
            android.print.PrintManager printManager = (android.print.PrintManager) getSystemService(android.content.Context.PRINT_SERVICE);
            if (printManager != null && mWebView != null) {
                String jobName = (docName != null && !docName.isEmpty()) ? docName : "SR_Enterprise_Invoice";
                android.print.PrintDocumentAdapter printAdapter = mWebView.createPrintDocumentAdapter(jobName);
                android.print.PrintAttributes attributes = new android.print.PrintAttributes.Builder()
                        .setMediaSize(android.print.PrintAttributes.MediaSize.ISO_A4)
                        .setResolution(new android.print.PrintAttributes.Resolution("sre_print", "Invoice Print", 300, 300))
                        .setMinMargins(android.print.PrintAttributes.Margins.NO_MARGINS)
                        .build();
                printManager.print(jobName, printAdapter, attributes);
            }
        } else {
            Toast.makeText(this, "প্রিন্ট সেবা বর্তমান ডিভাইসে সমর্থিত নয়", Toast.LENGTH_SHORT).show();
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        if (mWebView != null) {
            mWebView.saveState(outState);
        }
    }
}

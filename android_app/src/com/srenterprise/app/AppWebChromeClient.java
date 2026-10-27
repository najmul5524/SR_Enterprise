package com.srenterprise.app;

import android.content.Intent;
import android.net.Uri;
import android.view.View;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebView;
import android.widget.Toast;

public class AppWebChromeClient extends WebChromeClient {

    private final MainActivity mActivity;

    public AppWebChromeClient(MainActivity activity) {
        this.mActivity = activity;
    }

    @Override
    public void onProgressChanged(WebView view, int newProgress) {
        if (mActivity.mProgressBar != null) {
            mActivity.mProgressBar.setProgress(newProgress);
            if (newProgress == 100) {
                mActivity.mProgressBar.setVisibility(View.GONE);
            } else {
                mActivity.mProgressBar.setVisibility(View.VISIBLE);
            }
        }
    }

    @Override
    public void onPermissionRequest(final PermissionRequest request) {
        mActivity.runOnUiThread(new PermissionGrantRunner(request));
    }

    @Override
    public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback, FileChooserParams fileChooserParams) {
        if (mActivity.mFilePathCallback != null) {
            mActivity.mFilePathCallback.onReceiveValue(null);
        }
        mActivity.mFilePathCallback = filePathCallback;

        Intent takePictureIntent = new Intent(android.provider.MediaStore.ACTION_IMAGE_CAPTURE);
        boolean isCapture = false;
        if (fileChooserParams != null) {
            if (fileChooserParams.isCaptureEnabled()) {
                isCapture = true;
            } else {
                String[] acceptTypes = fileChooserParams.getAcceptTypes();
                if (acceptTypes != null) {
                    for (String t : acceptTypes) {
                        if (t != null && (t.contains("capture") || t.contains("camera"))) {
                            isCapture = true;
                            break;
                        }
                    }
                }
            }
        }

        try {
            android.content.ContentValues values = new android.content.ContentValues();
            values.put(android.provider.MediaStore.Images.Media.TITLE, "SRE_Cam_" + System.currentTimeMillis());
            values.put(android.provider.MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
            mActivity.mCameraCaptureUri = mActivity.getContentResolver().insert(
                android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values
            );
            takePictureIntent.putExtra(android.provider.MediaStore.EXTRA_OUTPUT, mActivity.mCameraCaptureUri);
            takePictureIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        } catch (Exception e) {
            try {
                java.io.File photoFile = new java.io.File(mActivity.getExternalCacheDir(), "camera_" + System.currentTimeMillis() + ".jpg");
                mActivity.mCameraCaptureUri = Uri.fromFile(photoFile);
                takePictureIntent.putExtra(android.provider.MediaStore.EXTRA_OUTPUT, mActivity.mCameraCaptureUri);
            } catch (Exception ex) {
                mActivity.mCameraCaptureUri = null;
            }
        }

        if (isCapture) {
            try {
                mActivity.startActivityForResult(takePictureIntent, MainActivity.FILE_CHOOSER_REQUEST_CODE);
                return true;
            } catch (Exception e) {}
        }

        Intent contentSelectionIntent = fileChooserParams.createIntent();
        Intent chooserIntent = Intent.createChooser(contentSelectionIntent, "ছবি বা ফাইল নির্বাচন করুন");
        chooserIntent.putExtra(Intent.EXTRA_INITIAL_INTENTS, new Intent[]{takePictureIntent});

        try {
            mActivity.startActivityForResult(chooserIntent, MainActivity.FILE_CHOOSER_REQUEST_CODE);
        } catch (Exception e) {
            mActivity.mFilePathCallback = null;
            Toast.makeText(mActivity, "ফাইল নির্বাচন করা যায়নি", Toast.LENGTH_SHORT).show();
            return false;
        }
        return true;
    }
}

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

        Intent intent = fileChooserParams.createIntent();
        try {
            mActivity.startActivityForResult(intent, MainActivity.FILE_CHOOSER_REQUEST_CODE);
        } catch (Exception e) {
            mActivity.mFilePathCallback = null;
            Toast.makeText(mActivity, "ফাইল নির্বাচন করা যায়নি", Toast.LENGTH_SHORT).show();
            return false;
        }
        return true;
    }
}

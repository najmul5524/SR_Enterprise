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

public class MainActivity extends Activity implements View.OnClickListener {

    public static final String APP_URL = "https://sr-enterprise.onrender.com/";
    public static final int REQUEST_CAMERA_PERMISSION = 1001;
    public static final int FILE_CHOOSER_REQUEST_CODE = 2001;

    public WebView mWebView;
    public ProgressBar mProgressBar;
    public LinearLayout mErrorLayout;
    public Button mBtnRetry;

    public ValueCallback<Uri[]> mFilePathCallback;
    private long backPressedTime = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            getWindow().setStatusBarColor(0xFF4C0519); // Maroon 950
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

        mWebView.addJavascriptInterface(new AppJsInterface(), "SRNativeApp");

        mWebView.setWebViewClient(new AppWebViewClient(this));
        mWebView.setWebChromeClient(new AppWebChromeClient(this));
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILE_CHOOSER_REQUEST_CODE) {
            if (mFilePathCallback != null) {
                Uri[] results = null;
                if (resultCode == RESULT_OK && data != null) {
                    String dataString = data.getDataString();
                    if (dataString != null) {
                        results = new Uri[]{Uri.parse(dataString)};
                    } else if (data.getClipData() != null) {
                        int count = data.getClipData().getItemCount();
                        results = new Uri[count];
                        for (int i = 0; i < count; i++) {
                            results[i] = data.getClipData().getItemAt(i).getUri();
                        }
                    }
                }
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

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        if (mWebView != null) {
            mWebView.saveState(outState);
        }
    }
}

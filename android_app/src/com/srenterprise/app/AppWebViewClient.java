package com.srenterprise.app;

import android.content.Intent;
import android.graphics.Bitmap;
import android.net.Uri;
import android.view.View;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class AppWebViewClient extends WebViewClient {

    private final MainActivity mActivity;

    public AppWebViewClient(MainActivity activity) {
        this.mActivity = activity;
    }

    @Override
    public void onPageStarted(WebView view, String url, Bitmap favicon) {
        super.onPageStarted(view, url, favicon);
        if (mActivity.mProgressBar != null) {
            mActivity.mProgressBar.setVisibility(View.VISIBLE);
        }
    }

    @Override
    public void onPageFinished(WebView view, String url) {
        super.onPageFinished(view, url);
        if (mActivity.mProgressBar != null) {
            mActivity.mProgressBar.setVisibility(View.GONE);
        }
    }

    @Override
    public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
        if (request.isForMainFrame()) {
            if (mActivity.mWebView != null) mActivity.mWebView.setVisibility(View.GONE);
            if (mActivity.mErrorLayout != null) mActivity.mErrorLayout.setVisibility(View.VISIBLE);
            if (mActivity.mProgressBar != null) mActivity.mProgressBar.setVisibility(View.GONE);
        }
    }

    @Override
    public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
        String url = request.getUrl().toString();
        if (url.startsWith("tel:") || url.startsWith("mailto:") || url.startsWith("whatsapp:")) {
            try {
                Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                mActivity.startActivity(intent);
                return true;
            } catch (Exception e) {
                return true;
            }
        }
        return false;
    }
}

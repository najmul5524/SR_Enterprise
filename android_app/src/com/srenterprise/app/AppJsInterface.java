package com.srenterprise.app;

import android.webkit.JavascriptInterface;

public class AppJsInterface {
    private MainActivity activity;

    public AppJsInterface(MainActivity activity) {
        this.activity = activity;
    }

    public AppJsInterface() {
        this.activity = null;
    }

    @JavascriptInterface
    public boolean isApp() {
        return true;
    }

    @JavascriptInterface
    public void printPage(String docName) {
        if (activity != null) {
            activity.triggerPrint(docName);
        }
    }

    @JavascriptInterface
    public void openCamera() {
        if (activity != null) {
            activity.openCameraFromJs();
        }
    }
}

package com.srenterprise.app;

public class JsEvalRunner implements Runnable {
    private final MainActivity mActivity;
    private final String mScript;

    public JsEvalRunner(MainActivity activity, String script) {
        this.mActivity = activity;
        this.mScript = script;
    }

    @Override
    public void run() {
        if (mActivity != null && mActivity.mWebView != null && mScript != null) {
            mActivity.mWebView.evaluateJavascript(mScript, null);
        }
    }
}

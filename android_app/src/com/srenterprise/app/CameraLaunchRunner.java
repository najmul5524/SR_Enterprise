package com.srenterprise.app;

public class CameraLaunchRunner implements Runnable {
    private final MainActivity mActivity;

    public CameraLaunchRunner(MainActivity activity) {
        this.mActivity = activity;
    }

    @Override
    public void run() {
        if (mActivity != null) {
            mActivity.launchNativeCamera();
        }
    }
}

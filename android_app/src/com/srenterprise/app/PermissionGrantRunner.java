package com.srenterprise.app;

import android.webkit.PermissionRequest;

public class PermissionGrantRunner implements Runnable {

    private final PermissionRequest mRequest;

    public PermissionGrantRunner(PermissionRequest request) {
        this.mRequest = request;
    }

    @Override
    public void run() {
        if (mRequest != null) {
            mRequest.grant(mRequest.getResources());
        }
    }
}

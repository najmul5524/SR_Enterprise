import os
import sys
import shutil
import subprocess
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
ANDROID_APP_DIR = BASE_DIR / "android_app"
SDK_DIR = Path(r"C:\Users\najmu\AppData\Local\Android\Sdk")
BUILD_TOOLS_DIR = SDK_DIR / "build-tools" / "34.0.0"
PLATFORM_JAR = SDK_DIR / "platforms" / "android-34" / "android.jar"
JAVA_HOME = Path(r"C:\Program Files\Android\Android Studio\jbr")
KEYSTORE_PATH = BASE_DIR / "android_app" / "sr_enterprise.keystore"
KEY_ALIAS = "sr_enterprise"
KEY_PASS = "sr_enterprise_2026"
OUTPUT_APK = BASE_DIR / "static" / "apk" / "SR_Enterprise.apk"

# Ensure environment has JAVA_HOME and PATH
env = os.environ.copy()
env["JAVA_HOME"] = str(JAVA_HOME)
env["PATH"] = f"{JAVA_HOME / 'bin'};{BUILD_TOOLS_DIR};{env.get('PATH', '')}"

def run_cmd(cmd_list, cwd=None):
    cmd_str = " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd_list)
    print(f"[EXEC] {cmd_str}")
    res = subprocess.run(cmd_list, cwd=cwd, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error output:\n{res.stderr}\n{res.stdout}")
        raise RuntimeError(f"Command failed with exit code {res.returncode}: {cmd_str}")
    return res.stdout

def create_icons():
    logo_path = BASE_DIR / "static" / "img" / "logo.png"
    if not logo_path.exists():
        raise FileNotFoundError(f"Logo not found at {logo_path}")
    
    img = Image.open(logo_path).convert("RGBA")
    
    sizes = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    
    for folder, size in sizes.items():
        folder_dir = ANDROID_APP_DIR / "res" / folder
        folder_dir.mkdir(parents=True, exist_ok=True)
        # Create square icon with padding to look great on Android
        icon = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        # Keep aspect ratio
        pad = int(size * 0.08)
        inner_size = size - (pad * 2)
        resized_logo = img.copy()
        resized_logo.thumbnail((inner_size, inner_size), Image.Resampling.LANCZOS)
        offset = ((size - resized_logo.width) // 2, (size - resized_logo.height) // 2)
        icon.paste(resized_logo, offset, resized_logo)
        icon.save(folder_dir / "ic_launcher.png", format="PNG")
    print("[ICONS] Mipmap icons created successfully.")

def write_app_files():
    # 1. Strings
    values_dir = ANDROID_APP_DIR / "res" / "values"
    values_dir.mkdir(parents=True, exist_ok=True)
    
    strings_xml = values_dir / "strings.xml"
    strings_xml.write_text("""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">SR Enterprise</string>
</resources>
""", encoding="utf-8")

    # 2. Colors
    colors_xml = values_dir / "colors.xml"
    colors_xml.write_text("""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="maroon_950">#4c0519</color>
    <color name="crimson_700">#be123c</color>
    <color name="orange_600">#ea580c</color>
    <color name="white">#ffffff</color>
</resources>
""", encoding="utf-8")

    # 3. Styles
    styles_xml = values_dir / "styles.xml"
    styles_xml.write_text("""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="@android:style/Theme.Light.NoTitleBar">
        <item name="android:windowBackground">@color/maroon_950</item>
    </style>
</resources>
""", encoding="utf-8")

    # 4. Layout
    layout_dir = ANDROID_APP_DIR / "res" / "layout"
    layout_dir.mkdir(parents=True, exist_ok=True)
    activity_main_xml = layout_dir / "activity_main.xml"
    activity_main_xml.write_text("""<?xml version="1.0" encoding="utf-8"?>
<RelativeLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="#fafaf9">

    <WebView
        android:id="@+id/webview"
        android:layout_width="match_parent"
        android:layout_height="match_parent" />

    <ProgressBar
        android:id="@+id/progress_bar"
        style="?android:attr/progressBarStyleHorizontal"
        android:layout_width="match_parent"
        android:layout_height="3dp"
        android:layout_alignParentTop="true"
        android:indeterminate="true"
        android:visibility="gone" />

    <LinearLayout
        android:id="@+id/error_layout"
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        android:gravity="center"
        android:orientation="vertical"
        android:padding="24dp"
        android:visibility="gone"
        android:background="#ffffff">

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="ইন্টারনেট সংযোগ নেই"
            android:textSize="20sp"
            android:textStyle="bold"
            android:textColor="#be123c"
            android:paddingBottom="8dp" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="অনুগ্রহ করে ওয়াইফাই অথবা মোবাইল ডাটা সংযোগ চালু করুন এবং পুনরায় চেষ্টা করুন।"
            android:textSize="14sp"
            android:gravity="center"
            android:textColor="#666666"
            android:paddingBottom="24dp" />

        <Button
            android:id="@+id/btn_retry"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="পুনরায় চেষ্টা করুন"
            android:background="#ea580c"
            android:textColor="#ffffff"
            android:paddingLeft="24dp"
            android:paddingRight="24dp" />
    </LinearLayout>

</RelativeLayout>
""", encoding="utf-8")

    # 5. AndroidManifest.xml
    manifest_xml = ANDROID_APP_DIR / "AndroidManifest.xml"
    manifest_xml.write_text("""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.srenterprise.app"
    android:versionCode="1"
    android:versionName="1.0.0">

    <uses-sdk
        android:minSdkVersion="21"
        android:targetSdkVersion="34" />

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />

    <uses-feature
        android:name="android.hardware.camera"
        android:required="false" />
    <uses-feature
        android:name="android.hardware.camera.autofocus"
        android:required="false" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/AppTheme"
        android:usesCleartextTraffic="true"
        android:hardwareAccelerated="true">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

    </application>

</manifest>
""", encoding="utf-8")

    # 6. Java source files (Top-level classes avoid JDK 25 inner-class D8 issue)
    src_dir = ANDROID_APP_DIR / "src" / "com" / "srenterprise" / "app"
    src_dir.mkdir(parents=True, exist_ok=True)
    
    # 6a. MainActivity.java
    (src_dir / "MainActivity.java").write_text("""package com.srenterprise.app;

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

        mWebView.addJavascriptInterface(new AppJsInterface(this), "SRNativeApp");

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
""", encoding="utf-8")

    # 6b. AppWebViewClient.java
    (src_dir / "AppWebViewClient.java").write_text("""package com.srenterprise.app;

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
        view.evaluateJavascript(
            "(function() {" +
            "  window.isNativeApp = true;" +
            "  document.documentElement.classList.add('in-mobile-app');" +
            "  var b = document.getElementById('apkDownloadBanner');" +
            "  if (b) { b.style.display = 'none'; b.remove(); }" +
            "})();", null);
    }

    @Override
    public void onPageFinished(WebView view, String url) {
        super.onPageFinished(view, url);
        if (mActivity.mProgressBar != null) {
            mActivity.mProgressBar.setVisibility(View.GONE);
        }
        view.evaluateJavascript(
            "(function() {" +
            "  window.isNativeApp = true;" +
            "  document.documentElement.classList.add('in-mobile-app');" +
            "  var b = document.getElementById('apkDownloadBanner');" +
            "  if (b) { b.style.display = 'none'; b.remove(); }" +
            "})();", null);
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
""", encoding="utf-8")

    # 6c. AppWebChromeClient.java
    (src_dir / "AppWebChromeClient.java").write_text("""package com.srenterprise.app;

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
""", encoding="utf-8")

    # 6d. PermissionGrantRunner.java
    (src_dir / "PermissionGrantRunner.java").write_text("""package com.srenterprise.app;

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
""", encoding="utf-8")

    # 6e. AppJsInterface.java
    (src_dir / "AppJsInterface.java").write_text("""package com.srenterprise.app;

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
}
""", encoding="utf-8")

    print("[APP] Project source files written successfully.")

def build_apk():
    build_dir = ANDROID_APP_DIR / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    
    compiled_res = build_dir / "compiled_res.zip"
    gen_dir = build_dir / "gen"
    gen_dir.mkdir(parents=True, exist_ok=True)
    bin_dir = build_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    aapt2 = BUILD_TOOLS_DIR / "aapt2.exe"
    javac = JAVA_HOME / "bin" / "javac.exe"
    d8 = BUILD_TOOLS_DIR / "d8.bat"
    zipalign = BUILD_TOOLS_DIR / "zipalign.exe"
    apksigner = BUILD_TOOLS_DIR / "apksigner.bat"
    keytool = JAVA_HOME / "bin" / "keytool.exe"

    # Step 1: AAPT2 compile resources
    print("\n--- Step 1: AAPT2 compile resources ---")
    run_cmd([
        str(aapt2), "compile",
        "--dir", str(ANDROID_APP_DIR / "res"),
        "-o", str(compiled_res)
    ])

    # Step 2: AAPT2 link to generate R.java and unaligned APK
    print("\n--- Step 2: AAPT2 link resources ---")
    unaligned_apk = build_dir / "unaligned.apk"
    run_cmd([
        str(aapt2), "link",
        "-I", str(PLATFORM_JAR),
        "--manifest", str(ANDROID_APP_DIR / "AndroidManifest.xml"),
        "--java", str(gen_dir),
        "-o", str(unaligned_apk),
        str(compiled_res),
        "--auto-add-overlay"
    ])

    # Step 3: Compile Java with javac
    print("\n--- Step 3: Compile Java classes ---")
    classes_dir = build_dir / "classes"
    classes_dir.mkdir(parents=True, exist_ok=True)
    
    java_files = list((ANDROID_APP_DIR / "src").rglob("*.java")) + list(gen_dir.rglob("*.java"))
    java_file_args = [str(f) for f in java_files]

    run_cmd([
        str(javac),
        "-source", "8",
        "-target", "8",
        "-g",
        "-bootclasspath", str(PLATFORM_JAR),
        "-cp", str(PLATFORM_JAR),
        "-d", str(classes_dir)
    ] + java_file_args)

    # Step 4: Convert .class files to DEX with d8
    print("\n--- Step 4: DEX compilation with D8 ---")
    class_files = [str(f) for f in classes_dir.rglob("*.class")]
    run_cmd([
        str(d8),
        "--lib", str(PLATFORM_JAR),
        "--min-api", "21",
        "--output", str(build_dir)
    ] + class_files)

    # Step 5: Add classes.dex into unaligned APK using jar/zip or aapt
    print("\n--- Step 5: Package classes.dex into APK ---")
    import zipfile
    with zipfile.ZipFile(unaligned_apk, "a") as z:
        z.write(build_dir / "classes.dex", arcname="classes.dex")

    # Step 6: Zipalign APK
    print("\n--- Step 6: Zipalign APK ---")
    aligned_apk = build_dir / "aligned.apk"
    run_cmd([
        str(zipalign),
        "-p", "-f", "4",
        str(unaligned_apk),
        str(aligned_apk)
    ])

    # Step 7: Create keystore if not exists
    print("\n--- Step 7: Keystore creation / check ---")
    if not KEYSTORE_PATH.exists():
        run_cmd([
            str(keytool),
            "-genkeypair",
            "-v",
            "-keystore", str(KEYSTORE_PATH),
            "-alias", KEY_ALIAS,
            "-keyalg", "RSA",
            "-keysize", "2048",
            "-validity", "10000",
            "-storepass", KEY_PASS,
            "-keypass", KEY_PASS,
            "-dname", "CN=SR Enterprise, OU=Management, O=SR Enterprise, L=Dhaka, ST=Dhaka, C=BD"
        ])
        print(f"[KEYSTORE] Generated new signed keystore at {KEYSTORE_PATH}")

    # Step 8: Sign APK with apksigner (v1, v2, v3)
    print("\n--- Step 8: Sign APK with apksigner ---")
    run_cmd([
        str(apksigner),
        "sign",
        "--ks", str(KEYSTORE_PATH),
        "--ks-key-alias", KEY_ALIAS,
        "--ks-pass", f"pass:{KEY_PASS}",
        "--key-pass", f"pass:{KEY_PASS}",
        "--out", str(OUTPUT_APK),
        str(aligned_apk)
    ])

    # Step 9: Verify APK signature
    print("\n--- Step 9: Verify APK Signature ---")
    verify_output = run_cmd([
        str(apksigner),
        "verify",
        "--verbose",
        str(OUTPUT_APK)
    ])
    print(verify_output)

    apk_size_mb = OUTPUT_APK.stat().st_size / (1024 * 1024)
    print(f"\n==========================================")
    print(f"[SUCCESS] Functional Signed APK successfully built!")
    print(f"Location: {OUTPUT_APK}")
    print(f"Size: {apk_size_mb:.2f} MB")
    print(f"==========================================")

if __name__ == "__main__":
    OUTPUT_APK.parent.mkdir(parents=True, exist_ok=True)
    create_icons()
    write_app_files()
    build_apk()

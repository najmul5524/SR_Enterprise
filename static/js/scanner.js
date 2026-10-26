// SR Enterprise QR Code & Barcode Camera Scanner Engine
class QRScannerEngine {
  constructor(elementId, onScanSuccessCallback) {
    this.elementId = elementId;
    this.onScanSuccess = onScanSuccessCallback;
    this.html5QrCode = null;
    this.isScanning = false;
    this.currentCameraId = null;
  }

  async start() {
    if (this.isScanning) return;

    try {
      if (!this.html5QrCode) {
        this.html5QrCode = new Html5Qrcode(this.elementId);
      }

      const config = {
        fps: 15,
        qrbox: (viewfinderWidth, viewfinderHeight) => {
          const minDim = Math.min(viewfinderWidth, viewfinderHeight);
          return {
            width: Math.max(160, Math.floor(minDim * 0.75)),
            height: Math.max(160, Math.floor(minDim * 0.75))
          };
        },
        aspectRatio: 1.0,
      };

      // 1. Try mobile rear camera first (facingMode: environment)
      try {
        await this.html5QrCode.start(
          { facingMode: "environment" },
          config,
          (decodedText, decodedResult) => {
            if (this.onScanSuccess) {
              this.onScanSuccess(decodedText, decodedResult);
            }
          },
          (errorMessage) => {}
        );
        this.isScanning = true;
        return;
      } catch (modeErr) {
        console.warn("facingMode 'environment' not direct, fallback to device enumeration...", modeErr);
      }

      // 2. Fallback: enumerate available cameras
      const cameras = await Html5Qrcode.getCameras();
      if (!cameras || cameras.length === 0) {
        showToast("কোন ক্যামেরা ডিভাইস পাওয়া যায়নি!", "error");
        return;
      }

      let targetCamera = cameras[cameras.length - 1]; // usually back camera on phones
      for (const cam of cameras) {
        const lbl = (cam.label || '').toLowerCase();
        if (lbl.includes('back') || lbl.includes('rear') || lbl.includes('environment')) {
          targetCamera = cam;
          break;
        }
      }

      this.currentCameraId = targetCamera.id;

      await this.html5QrCode.start(
        targetCamera.id,
        config,
        (decodedText, decodedResult) => {
          if (this.onScanSuccess) {
            this.onScanSuccess(decodedText, decodedResult);
          }
        },
        (errorMessage) => {}
      );

      this.isScanning = true;
    } catch (err) {
      console.error("Camera start failed:", err);
      showToast("ক্যামেরা অন করা যায়নি: " + (err.message || err), "error");
    }
  }

  async stop() {
    if (this.html5QrCode && this.isScanning) {
      try {
        await this.html5QrCode.stop();
      } catch (err) {
        console.error("Camera stop error:", err);
      } finally {
        this.isScanning = false;
      }
    }
  }

  async toggleTorch() {
    if (this.html5QrCode && this.isScanning) {
      try {
        await this.html5QrCode.applyVideoConstraints({
          advanced: [{ torch: true }]
        });
      } catch (e) {
        showToast("এই ডিভাইসে টর্চ সাপোর্ট নেই", "warning");
      }
    }
  }
}

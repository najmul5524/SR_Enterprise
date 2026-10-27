/**
 * SR Enterprise - Universal Smart Scanner & 4-Corner Perspective Cropper
 * Mobile Camera & Gallery integration with CamScanner-style perspective de-skewing & magic filters.
 */

const SmartScanner = (function () {
  let modal = null;
  let canvas = null;
  let ctx = null;
  let previewCanvas = null;
  let previewCtx = null;

  let currentImage = null; // HTMLImageElement
  let originalRotation = 0; // 0, 90, 180, 270

  // 4 corners in canvas display coordinates: [TL, TR, BR, BL]
  let corners = [];
  let activeCorner = -1;
  let dragOffset = { x: 0, y: 0 };
  let imageDisplayScale = 1;
  let imageDisplayOffset = { x: 0, y: 0 };

  // Current state
  let currentStep = 'crop'; // 'crop' | 'filter'
  let currentFilter = 'magic'; // 'original' | 'magic' | 'bw' | 'gray'
  let warpedCanvas = null; // intermediate canvas holding the straightened rectangular image

  // Target input & callback
  let targetFileInput = null;
  let onCompleteCallback = null;
  let previewElement = null;

  // Touch radius for easier dragging on mobile screens
  const HANDLE_RADIUS = 16;
  const TOUCH_SLOP = 32;

  // Live Camera state
  let cameraModal = null;
  let videoEl = null;
  let cameraStream = null;
  let currentFacingMode = 'environment';
  let cameraOptions = null;
  let _isFinishing = false;
  let _handlersAttached = false;

  function init() {
    if (!document.getElementById('smartScannerModal')) {
      const modalHtml = `
    <!-- 1. LIVE CAMERA MODAL -->
    <div id="smartScannerCameraModal" class="fixed inset-0 z-[10000] hidden bg-black flex flex-col justify-between select-none">
      
      <!-- Top Bar -->
      <div class="absolute top-0 inset-x-0 bg-gradient-to-b from-black/80 via-black/40 to-transparent p-4 flex items-center justify-between z-20">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-xl bg-orangeBrand-500/30 text-orangeBrand-400 flex items-center justify-center text-lg border border-orangeBrand-500/40">
            📸
          </div>
          <div>
            <h3 class="text-sm font-black text-white leading-none">লাইভ ক্যামেরা স্ক্যানার</h3>
            <p class="text-[10px] text-slate-300 mt-0.5">পণ্য বা মেমো ফ্রেমে রাখুন ও ছবি তুলুন</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button type="button" id="scannerCameraFlipBtn" onclick="SmartScanner.flipCamera()" class="p-2.5 rounded-full bg-slate-800/80 hover:bg-slate-700 text-white text-xs font-bold transition border border-slate-700/80 shadow-md" title="ক্যামেরা ঘোরান">
            <span>🔄</span>
          </button>
          <button type="button" onclick="SmartScanner.closeCamera()" class="p-2.5 rounded-full bg-rose-950/80 hover:bg-rose-900 text-rose-300 text-xs font-black transition border border-rose-800/60 shadow-md" title="বন্ধ করুন">
            ✕
          </button>
        </div>
      </div>

      <!-- Video Viewfinder -->
      <div class="relative flex-1 w-full h-full flex items-center justify-center overflow-hidden bg-black">
        <video id="smartScannerVideo" autoplay playsinline muted class="w-full h-full object-cover"></video>
        
        <!-- Viewfinder Guide Box -->
        <div class="pointer-events-none absolute inset-6 sm:inset-12 border-2 border-dashed border-orangeBrand-400/80 rounded-3xl flex flex-col justify-between p-4 shadow-[0_0_0_9999px_rgba(0,0,0,0.45)]">
          <div class="flex justify-between items-start">
            <div class="w-7 h-7 border-t-4 border-l-4 border-orangeBrand-500 rounded-tl-xl shadow-sm"></div>
            <div class="w-7 h-7 border-t-4 border-r-4 border-orangeBrand-500 rounded-tr-xl shadow-sm"></div>
          </div>
          <div class="text-center px-2">
            <span class="inline-block px-3.5 py-1.5 bg-black/70 backdrop-blur-md text-orangeBrand-300 text-[11px] font-bold rounded-full border border-orangeBrand-500/40 shadow-lg">
              💡 ছবি তোলার পর CamScanner-এর মতো ৪ কোণা সোজা করার অপশন পাবেন
            </span>
          </div>
          <div class="flex justify-between items-end">
            <div class="w-7 h-7 border-b-4 border-l-4 border-orangeBrand-500 rounded-bl-xl shadow-sm"></div>
            <div class="w-7 h-7 border-b-4 border-r-4 border-orangeBrand-500 rounded-br-xl shadow-sm"></div>
          </div>
        </div>
      </div>

      <!-- Bottom Bar: Capture Controls -->
      <div class="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/95 via-black/70 to-transparent p-6 pb-8 flex items-center justify-around z-20">
        <!-- Gallery Fallback Button -->
        <button type="button" id="scannerCameraGalleryBtn" onclick="SmartScanner.fallbackToGallery()" class="flex flex-col items-center gap-1.5 text-slate-300 hover:text-white transition touch-press">
          <div class="w-12 h-12 rounded-2xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 flex items-center justify-center text-xl shadow-md">
            📁
          </div>
          <span class="text-[11px] font-bold">গ্যালারি</span>
        </button>

        <!-- Main Shutter Button -->
        <button type="button" id="scannerCameraSnapBtn" onclick="SmartScanner.snapPhoto()" class="w-20 h-20 rounded-full border-4 border-white p-1 shadow-2xl transition transform active:scale-90 flex items-center justify-center bg-transparent group touch-press">
          <div class="w-full h-full rounded-full bg-gradient-to-tr from-orangeBrand-500 to-crimson-600 group-hover:opacity-95 shadow-lg flex items-center justify-center text-white text-3xl font-black">
            📸
          </div>
        </button>

        <!-- Cancel / Close -->
        <button type="button" onclick="SmartScanner.closeCamera()" class="flex flex-col items-center gap-1.5 text-slate-400 hover:text-white transition touch-press">
          <div class="w-12 h-12 rounded-2xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 flex items-center justify-center text-base shadow-md">
            ✕
          </div>
          <span class="text-[11px] font-bold">বাতিল</span>
        </button>
      </div>
    </div>

    <!-- 2. 4-CORNER PERSPECTIVE CROP & FILTER MODAL -->
    <div id="smartScannerModal" class="fixed inset-0 z-[9999] hidden bg-slate-950/90 backdrop-blur-md flex flex-col justify-between select-none">
      
      <!-- Top Bar -->
      <div class="bg-slate-900/90 border-b border-slate-800 px-4 py-3 flex items-center justify-between z-10">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-xl bg-orangeBrand-500/20 text-orangeBrand-500 flex items-center justify-center text-lg border border-orangeBrand-500/30">
            📸
          </div>
          <div>
            <h3 class="text-sm font-black text-white leading-none">স্মার্ট স্ক্যান ও ক্রপ (Smart Scanner)</h3>
            <p id="scannerSubtitle" class="text-[10px] text-slate-300 mt-0.5">৪ কোণা টেনে ছবি সোজা করুন (CamScanner-এর মতো)</p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button type="button" id="scannerRotateBtn" onclick="SmartScanner.rotate90()" class="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition flex items-center gap-1 border border-slate-700" title="ছবি ৯০° ঘোরান">
            <span>🔄</span> <span class="hidden sm:inline">ঘোরান</span>
          </button>
          <button type="button" id="scannerResetBtn" onclick="SmartScanner.resetCornersToFull()" class="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition flex items-center gap-1 border border-slate-700" title="পুরো ছবি সিলেক্ট করুন">
            <span>🔲</span> <span class="hidden sm:inline">পুরো ছবি</span>
          </button>
          <button type="button" onclick="SmartScanner.close()" class="p-2 rounded-xl bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 text-xs font-black transition border border-rose-800/50">
            ✕
          </button>
        </div>
      </div>

      <!-- Main Canvas Work Area -->
      <div id="scannerWorkArea" class="flex-1 relative overflow-hidden flex items-center justify-center p-2 sm:p-4 touch-none">
        
        <!-- Step 1: Crop View (Interactive Canvas with 4 corner pins) -->
        <div id="cropViewContainer" class="relative w-full h-full flex items-center justify-center">
          <canvas id="scannerCanvas" class="max-w-full max-h-[68vh] rounded-xl shadow-2xl bg-black cursor-crosshair"></canvas>
          
          <!-- Zoom Magnifier Loupe for Precision Pin Placement -->
          <div id="scannerLoupe" class="hidden absolute pointer-events-none w-24 h-24 rounded-full border-2 border-white shadow-2xl bg-black overflow-hidden z-30">
            <canvas id="loupeCanvas" width="96" height="96"></canvas>
            <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div class="w-2.5 h-2.5 rounded-full border border-orangeBrand-500 bg-orangeBrand-500/50"></div>
            </div>
          </div>
        </div>

        <!-- Step 2: Filter / Preview View (Straightened result with CamScanner filter tabs) -->
        <div id="filterViewContainer" class="hidden relative w-full h-full flex flex-col items-center justify-center">
          <canvas id="previewCanvas" class="max-w-full max-h-[58vh] rounded-xl shadow-2xl bg-black"></canvas>
        </div>

      </div>

      <!-- Bottom Toolbar & Actions -->
      <div class="bg-slate-900/95 border-t border-slate-800 p-3 sm:px-6 sm:py-4 z-10 space-y-3">
        
        <!-- Filter Tabs (Visible only in Filter / Preview Step) -->
        <div id="scannerFilterTabs" class="hidden flex items-center justify-center gap-2 overflow-x-auto pb-1">
          <button type="button" onclick="SmartScanner.applyFilter('magic')" data-filter="magic" class="scanner-filter-btn px-3 py-1.5 rounded-xl text-xs font-black transition flex items-center gap-1.5 border border-orangeBrand-500 bg-orangeBrand-500/20 text-orangeBrand-500">
            <span>🪄</span> <span>ম্যাজিক কালার (স্মার্ট স্ক্যান)</span>
          </button>
          <button type="button" onclick="SmartScanner.applyFilter('bw')" data-filter="bw" class="scanner-filter-btn px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 border border-slate-700 bg-slate-800 text-slate-300">
            <span>📄</span> <span>ডকুমেন্ট / মেমো (B&W)</span>
          </button>
          <button type="button" onclick="SmartScanner.applyFilter('original')" data-filter="original" class="scanner-filter-btn px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 border border-slate-700 bg-slate-800 text-slate-300">
            <span>🌈</span> <span>স্বাভাবিক (Original)</span>
          </button>
          <button type="button" onclick="SmartScanner.applyFilter('gray')" data-filter="gray" class="scanner-filter-btn px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 border border-slate-700 bg-slate-800 text-slate-300">
            <span>🌑</span> <span>সাদাকালো (Gray)</span>
          </button>
        </div>

        <!-- Main Action Buttons -->
        <div class="flex items-center justify-between gap-2">
          
          <div class="flex items-center gap-1.5">
            <!-- Back button (in filter step) -->
            <button type="button" id="scannerBackBtn" onclick="SmartScanner.backToCrop()" class="hidden px-3.5 py-2 sm:px-4 sm:py-2.5 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 transition flex items-center gap-1 border border-slate-700">
              <span>↩️</span> <span class="hidden sm:inline">কোণা পরিবর্তন (Re-Crop)</span><span class="sm:hidden">কোণা</span>
            </button>
            <!-- Cancel / Close button -->
            <button type="button" onclick="SmartScanner.close()" class="px-3.5 py-2 sm:px-4 sm:py-2.5 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition flex items-center gap-1 border border-slate-700">
              <span>✕</span> <span>বাতিল</span>
            </button>
          </div>

          <!-- Primary Actions -->
          <div class="flex items-center gap-2 ml-auto">
            <!-- Distinct, vibrant Filter & Preview Button -->
            <button type="button" id="scannerCropBtn" onclick="SmartScanner.processPerspectiveCrop()" class="px-4 py-2 sm:px-5 sm:py-2.5 bg-gradient-to-r from-amber-500 via-orange-500 to-orangeBrand-600 hover:opacity-95 text-white font-black rounded-xl text-xs shadow-lg shadow-orange-500/25 border border-orange-400/40 transition flex items-center justify-center gap-1.5 touch-press">
              <span>🪄</span> <span>ফিল্টার ও প্রিভিউ</span>
            </button>

            <!-- Complete / Apply Button -->
            <button type="button" id="scannerApplyBtn" onclick="SmartScanner.finishAndApply()" class="px-4 py-2 sm:px-6 sm:py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:opacity-95 text-white font-black rounded-xl text-xs shadow-lg shadow-emerald-600/25 transition flex items-center justify-center gap-1.5 touch-press">
              <span>✅</span> <span>সম্পন্ন করুন (Apply)</span>
            </button>
          </div>

        </div>

      </div>

    </div>
    `;

      document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    modal = document.getElementById('smartScannerModal');
    cameraModal = document.getElementById('smartScannerCameraModal');
    videoEl = document.getElementById('smartScannerVideo');
    canvas = document.getElementById('scannerCanvas');
    if (canvas) ctx = canvas.getContext('2d');
    previewCanvas = document.getElementById('previewCanvas');
    if (previewCanvas) previewCtx = previewCanvas.getContext('2d');

    if (!_handlersAttached && canvas) {
      setupInteractionHandlers();
      _handlersAttached = true;
    }
  }

  // ==================== LIVE CAMERA LOGIC ====================
  function setCameraOptions(options) {
    cameraOptions = options;
  }

  function onNativeCameraResult(dataUrl) {
    if (!dataUrl) return;
    const opts = cameraOptions || {};
    open(dataUrl, opts);
  }

  function checkNativePhoto() {
    if (window.SRNativeApp && typeof window.SRNativeApp.getLastCapturedPhoto === 'function') {
      try {
        const photo = window.SRNativeApp.getLastCapturedPhoto();
        if (photo && photo.startsWith('data:image')) {
          onNativeCameraResult(photo);
        }
      } catch (e) {
        console.warn("[SmartScanner] checkNativePhoto error:", e);
      }
    }
  }

  async function openCamera(options = {}) {
    cameraOptions = options;
    init();

    // 1. If running inside Android native app, trigger native camera directly!
    if (window.SRNativeApp && typeof window.SRNativeApp.openCamera === 'function') {
      window.SRNativeApp.openCamera();
      return;
    }

    // 2. Check secure context in Web browsers
    if (!window.isSecureContext && window.location.protocol === 'http:' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      if (window.showToast) {
        showToast("ব্রাউজারে ক্যামেরা ব্যবহারের জন্য HTTPS অথবা localhost প্রয়োজন।", "warning");
      }
      fallbackToNativeOrInput();
      return;
    }

    // 3. If navigator.mediaDevices is supported (Desktop Web, Laptop, Mobile Chrome/Safari)
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      cameraModal = document.getElementById('smartScannerCameraModal');
      videoEl = document.getElementById('smartScannerVideo');
      cameraModal.classList.remove('hidden');

      let stream = null;
      let lastErr = null;

      stopCameraStream();

      // Attempt A: Preferred facingMode (ideal on mobile phones with rear camera)
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: currentFacingMode } },
          audio: false
        });
      } catch (errA) {
        lastErr = errA;
      }

      // Attempt B: Basic video constraint (perfect for laptop webcams, desktop USB cameras)
      if (!stream) {
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false
          });
        } catch (errB) {
          lastErr = errB;
        }
      }

      // Attempt C: Enumerate devices and select first video device
      if (!stream && navigator.mediaDevices.enumerateDevices) {
        try {
          const devices = await navigator.mediaDevices.enumerateDevices();
          const videoDevs = devices.filter(d => d.kind === 'videoinput');
          if (videoDevs.length > 0) {
            stream = await navigator.mediaDevices.getUserMedia({
              video: { deviceId: { exact: videoDevs[0].deviceId } },
              audio: false
            });
          }
        } catch (errC) {
          lastErr = errC;
        }
      }

      if (stream) {
        cameraStream = stream;
        videoEl.srcObject = cameraStream;
        videoEl.muted = true;
        videoEl.setAttribute('playsinline', '');
        try {
          await videoEl.play();
          return;
        } catch (playErr) {
          console.warn("[SmartScanner] video.play() failed:", playErr);
        }
      }

      // If we reach here, camera stream failed
      console.warn("[SmartScanner] getUserMedia failed:", lastErr);
      closeCamera();

      if (lastErr && (lastErr.name === 'NotAllowedError' || lastErr.name === 'PermissionDeniedError')) {
        if (window.showToast) {
          showToast("ব্রাউজারে ক্যামেরা ব্যবহারের অনুমতি (Permission) দিন।", "error");
        }
        return;
      }
      if (lastErr && lastErr.name === 'NotFoundError') {
        if (window.showToast) {
          showToast("কোনো ক্যামেরা খুঁজে পাওয়া যায়নি। ফাইল বা গ্যালারি থেকে ছবি দিন।", "info");
        }
      }
    }

    // 4. Fallback to native or file input
    fallbackToNativeOrInput();
  }

  function stopCameraStream() {
    if (cameraStream) {
      try {
        cameraStream.getTracks().forEach(track => track.stop());
      } catch (e) {}
      cameraStream = null;
    }
    if (videoEl) {
      try {
        videoEl.srcObject = null;
      } catch (e) {}
    }
  }

  function closeCamera() {
    stopCameraStream();
    if (cameraModal) {
      cameraModal.classList.add('hidden');
    }
  }

  function flipCamera() {
    currentFacingMode = (currentFacingMode === 'environment') ? 'user' : 'environment';
    openCamera(cameraOptions);
  }

  function snapPhoto() {
    videoEl = document.getElementById('smartScannerVideo');
    if (!videoEl || !cameraStream) {
      fallbackToNativeOrInput();
      return;
    }

    const vw = videoEl.videoWidth || 1280;
    const vh = videoEl.videoHeight || 720;
    const snapCanvas = document.createElement('canvas');
    snapCanvas.width = vw;
    snapCanvas.height = vh;
    const sCtx = snapCanvas.getContext('2d');
    sCtx.drawImage(videoEl, 0, 0, vw, vh);

    const capturedDataUrl = snapCanvas.toDataURL('image/jpeg', 0.95);
    const savedOptions = cameraOptions || {};

    closeCamera();

    // Seamlessly open 4-corner crop view with captured photo!
    open(capturedDataUrl, savedOptions);
  }

  function fallbackToGallery() {
    closeCamera();
    if (cameraOptions) {
      if (cameraOptions.galleryInputId) {
        const gEl = (typeof cameraOptions.galleryInputId === 'string') 
          ? document.getElementById(cameraOptions.galleryInputId) 
          : cameraOptions.galleryInputId;
        if (gEl) {
          gEl.click();
          return;
        }
      }
      if (cameraOptions.targetInput) {
        cameraOptions.targetInput.click();
        return;
      }
    }
  }

  function fallbackToNativeOrInput() {
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || ('ontouchstart' in window && navigator.maxTouchPoints > 1);

    if (isMobile && cameraOptions && cameraOptions.cameraInputId) {
      const cEl = (typeof cameraOptions.cameraInputId === 'string')
        ? document.getElementById(cameraOptions.cameraInputId)
        : cameraOptions.cameraInputId;
      if (cEl) {
        cEl.click();
        return;
      }
    }
    if (cameraOptions && cameraOptions.targetInput) {
      cameraOptions.targetInput.click();
      return;
    }
    if (window.showToast) {
      showToast("ক্যামেরা ওপেন করা যায়নি। গ্যালারি থেকে ছবি নির্বাচন করুন।", "info");
    }
  }

  // ==================== INTERACTION HANDLERS ====================
  function setupInteractionHandlers() {
    const getPos = (e) => {
      const rect = canvas.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const rW = rect.width || canvas.width || 1;
      const rH = rect.height || canvas.height || 1;
      return {
        x: (clientX - rect.left) * (canvas.width / rW),
        y: (clientY - rect.top) * (canvas.height / rH),
        screenX: clientX,
        screenY: clientY
      };
    };

    const handleStart = (e) => {
      if (currentStep !== 'crop') return;
      const pos = getPos(e);
      let closestIdx = -1;
      let minDistance = Infinity;

      for (let i = 0; i < 4; i++) {
        const dx = corners[i].x - pos.x;
        const dy = corners[i].y - pos.y;
        const dist = Math.hypot(dx, dy);
        if (dist < minDistance) {
          minDistance = dist;
          closestIdx = i;
        }
      }

      const clientW = canvas.clientWidth || canvas.width || 1;
      const scaleFactor = canvas.width / clientW;

      if (minDistance <= TOUCH_SLOP * scaleFactor) {
        activeCorner = closestIdx;
        dragOffset.x = corners[closestIdx].x - pos.x;
        dragOffset.y = corners[closestIdx].y - pos.y;
        showLoupe(pos.screenX, pos.screenY, corners[activeCorner]);
        e.preventDefault();
      }
    };

    const handleMove = (e) => {
      if (activeCorner === -1 || currentStep !== 'crop') return;
      const pos = getPos(e);

      // Clamp inside canvas bounds
      const newX = Math.max(0, Math.min(canvas.width, pos.x + dragOffset.x));
      const newY = Math.max(0, Math.min(canvas.height, pos.y + dragOffset.y));

      corners[activeCorner].x = newX;
      corners[activeCorner].y = newY;

      drawCropOverlay();
      showLoupe(pos.screenX, pos.screenY, corners[activeCorner]);
      e.preventDefault();
    };

    const handleEnd = () => {
      if (activeCorner !== -1) {
        activeCorner = -1;
        hideLoupe();
        drawCropOverlay();
      }
    };

    canvas.addEventListener('mousedown', handleStart);
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleEnd);

    canvas.addEventListener('touchstart', handleStart, { passive: false });
    window.addEventListener('touchmove', handleMove, { passive: false });
    window.addEventListener('touchend', handleEnd);
  }

  function showLoupe(screenX, screenY, corner) {
    const loupe = document.getElementById('scannerLoupe');
    const loupeCanvas = document.getElementById('loupeCanvas');
    if (!loupe || !loupeCanvas) return;
    const loupeCtx = loupeCanvas.getContext('2d');

    loupe.style.left = `${screenX - 48}px`;
    loupe.style.top = `${screenY - 110}px`;
    loupe.classList.remove('hidden');

    loupeCtx.clearRect(0, 0, 96, 96);
    // Draw 3x zoomed portion around corner
    loupeCtx.drawImage(
      canvas,
      corner.x - 16, corner.y - 16, 32, 32,
      0, 0, 96, 96
    );
  }

  function hideLoupe() {
    const loupe = document.getElementById('scannerLoupe');
    if (loupe) loupe.classList.add('hidden');
  }

  // ==================== OPEN SMART SCANNER ====================
  function open(source, options = {}) {
    _isFinishing = false; // Always allow user to open scanner
    init();

    if (!source) {
      console.warn("[SmartScanner] No source provided to SmartScanner.open");
      return;
    }
    if (typeof source === 'string' && (source.trim() === '' || source === window.location.href)) {
      console.warn("[SmartScanner] Empty or current page URL provided to SmartScanner.open");
      return;
    }
    if (source instanceof HTMLImageElement) {
      const raw = source.getAttribute('src');
      if (!raw || raw.trim() === '' || raw === window.location.href) {
        console.warn("[SmartScanner] HTMLImageElement has empty or current page src");
        return;
      }
    }

    targetFileInput = options.targetInput || null;
    onCompleteCallback = options.onComplete || null;
    previewElement = options.previewElement || null;
    originalRotation = 0;
    currentFilter = options.defaultFilter || 'magic';
    currentStep = 'crop';

    document.getElementById('cropViewContainer').classList.remove('hidden');
    document.getElementById('filterViewContainer').classList.add('hidden');
    document.getElementById('scannerCropBtn').classList.remove('hidden');
    document.getElementById('scannerApplyBtn').classList.remove('hidden');
    document.getElementById('scannerBackBtn').classList.add('hidden');
    document.getElementById('scannerFilterTabs').classList.add('hidden');
    document.getElementById('scannerRotateBtn').classList.remove('hidden');
    document.getElementById('scannerResetBtn').classList.remove('hidden');
    document.getElementById('scannerSubtitle').innerText = "৪ কোণা টেনে ছবি সোজা করুন (CamScanner-এর মতো)";

    // Show modal immediately
    modal.classList.remove('hidden');

    const img = new Image();

    // Only set crossOrigin for remote absolute URLs on a DIFFERENT host (never for same-origin, data:, or blob:)
    if (typeof source === 'string' && (source.startsWith('http://') || source.startsWith('https://'))) {
      try {
        const urlObj = new URL(source);
        if (urlObj.hostname !== window.location.hostname) {
          img.crossOrigin = 'anonymous';
        }
      } catch (e) {}
    }

    const onImgReady = function () {
      currentImage = img;
      renderImageToCanvas();
    };

    img.onload = onImgReady;
    img.onerror = function (e) {
      console.error("[SmartScanner] Image load failed:", e);
      // If failed with crossOrigin, retry with fresh image without crossOrigin
      if (img.crossOrigin) {
        const retryImg = new Image();
        retryImg.onload = function () {
          currentImage = retryImg;
          renderImageToCanvas();
        };
        retryImg.onerror = function () {
          if (window.showToast) showToast("ছবি লোড করতে সমস্যা হয়েছে", "error");
        };
        retryImg.src = (typeof source === 'string') ? source : (source.src || '');
        return;
      }
      if (window.showToast) {
        showToast("ছবি লোড করতে সমস্যা হয়েছে", "error");
      }
    };

    if (source instanceof File || source instanceof Blob) {
      const reader = new FileReader();
      reader.onload = (e) => { img.src = e.target.result; };
      reader.readAsDataURL(source);
    } else if (typeof source === 'string') {
      img.src = source;
      if (img.complete && img.naturalWidth > 0) {
        onImgReady();
      }
    } else if (source instanceof HTMLImageElement) {
      img.src = source.src;
      if (img.complete && img.naturalWidth > 0) {
        onImgReady();
      }
    }
  }

  function renderImageToCanvas() {
    if (!currentImage) return;

    const nw = currentImage.naturalWidth || currentImage.width || 800;
    const nh = currentImage.naturalHeight || currentImage.height || 600;
    if (nw === 0 || nh === 0) return;

    // Determine dimensions considering rotation
    const isRotated = (originalRotation % 180 !== 0);
    const dw = isRotated ? nh : nw;
    const dh = isRotated ? nw : nh;

    // Scale to max screen bounds
    const maxW = Math.min(window.innerWidth - 32, 900);
    const maxH = Math.min(window.innerHeight * 0.68, 800);
    const scale = Math.min(maxW / dw, maxH / dh, 1);

    canvas.width = Math.round(dw * scale);
    canvas.height = Math.round(dh * scale);

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate((originalRotation * Math.PI) / 180);

    const drawW = (originalRotation % 180 === 0) ? canvas.width : canvas.height;
    const drawH = (originalRotation % 180 === 0) ? canvas.height : canvas.width;
    ctx.drawImage(currentImage, -drawW / 2, -drawH / 2, drawW, drawH);
    ctx.restore();

    // Initialize 4 corners with a smart 6% inner margin
    const insetX = canvas.width * 0.06;
    const insetY = canvas.height * 0.06;

    corners = [
      { x: insetX, y: insetY }, // TL
      { x: canvas.width - insetX, y: insetY }, // TR
      { x: canvas.width - insetX, y: canvas.height - insetY }, // BR
      { x: insetX, y: canvas.height - insetY } // BL
    ];

    drawCropOverlay();
  }

  function resetCornersToFull() {
    if (!canvas) return;
    corners = [
      { x: 2, y: 2 },
      { x: canvas.width - 2, y: 2 },
      { x: canvas.width - 2, y: canvas.height - 2 },
      { x: 2, y: canvas.height - 2 }
    ];
    drawCropOverlay();
  }

  function rotate90() {
    originalRotation = (originalRotation + 90) % 360;
    renderImageToCanvas();
  }

  function drawCropOverlay() {
    if (!ctx || corners.length < 4) return;

    // 1. Redraw base image
    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate((originalRotation * Math.PI) / 180);
    const drawW = (originalRotation % 180 === 0) ? canvas.width : canvas.height;
    const drawH = (originalRotation % 180 === 0) ? canvas.height : canvas.width;
    ctx.drawImage(currentImage, -drawW / 2, -drawH / 2, drawW, drawH);
    ctx.restore();

    // 2. Draw dark semi-transparent mask OUTSIDE the 4-corner polygon
    ctx.save();
    ctx.fillStyle = 'rgba(2, 6, 23, 0.65)';
    ctx.beginPath();
    ctx.rect(0, 0, canvas.width, canvas.height);
    // Cut out the quadrilateral
    ctx.moveTo(corners[0].x, corners[0].y);
    ctx.lineTo(corners[3].x, corners[3].y);
    ctx.lineTo(corners[2].x, corners[2].y);
    ctx.lineTo(corners[1].x, corners[1].y);
    ctx.closePath();
    ctx.fill('evenodd');

    // 3. Draw glowing quadrilateral border lines
    ctx.beginPath();
    ctx.moveTo(corners[0].x, corners[0].y);
    ctx.lineTo(corners[1].x, corners[1].y);
    ctx.lineTo(corners[2].x, corners[2].y);
    ctx.lineTo(corners[3].x, corners[3].y);
    ctx.closePath();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = '#f97316'; // orangeBrand
    ctx.shadowColor = '#ea580c';
    ctx.shadowBlur = 8;
    ctx.stroke();

    // 4. Draw rule-of-thirds grid lines inside quad
    ctx.beginPath();
    ctx.lineWidth = 0.75;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.shadowBlur = 0;
    for (let i = 1; i <= 2; i++) {
      const f = i / 3;
      // Horizontal grid
      const lx = (1 - f) * corners[0].x + f * corners[3].x;
      const ly = (1 - f) * corners[0].y + f * corners[3].y;
      const rx = (1 - f) * corners[1].x + f * corners[2].x;
      const ry = (1 - f) * corners[1].y + f * corners[2].y;
      ctx.moveTo(lx, ly);
      ctx.lineTo(rx, ry);

      // Vertical grid
      const tx = (1 - f) * corners[0].x + f * corners[1].x;
      const ty = (1 - f) * corners[0].y + f * corners[1].y;
      const bx = (1 - f) * corners[3].x + f * corners[2].x;
      const by = (1 - f) * corners[3].y + f * corners[2].y;
      ctx.moveTo(tx, ty);
      ctx.lineTo(bx, by);
    }
    ctx.stroke();

    // 5. Draw 4 draggable corner handles
    const labels = ['↖', '↗', '↘', '↙'];
    corners.forEach((c, idx) => {
      // Outer glow circle
      ctx.beginPath();
      ctx.arc(c.x, c.y, HANDLE_RADIUS, 0, Math.PI * 2);
      ctx.fillStyle = idx === activeCorner ? '#ea580c' : '#ffffff';
      ctx.shadowColor = 'rgba(0,0,0,0.8)';
      ctx.shadowBlur = 6;
      ctx.fill();

      // Inner dot
      ctx.beginPath();
      ctx.arc(c.x, c.y, HANDLE_RADIUS - 4, 0, Math.PI * 2);
      ctx.fillStyle = idx === activeCorner ? '#ffffff' : '#f97316';
      ctx.shadowBlur = 0;
      ctx.fill();

      // Mini corner icon
      ctx.fillStyle = idx === activeCorner ? '#f97316' : '#ffffff';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(labels[idx], c.x, c.y);
    });

    ctx.restore();
  }

  // ==================== BILINEAR PERSPECTIVE WARP ====================
  function processPerspectiveCrop() {
    if (!currentImage || corners.length < 4) return;

    // Calculate natural dimensions and source canvas in memory
    const srcCanvas = document.createElement('canvas');
    srcCanvas.width = canvas.width;
    srcCanvas.height = canvas.height;
    const sCtx = srcCanvas.getContext('2d');
    sCtx.drawImage(canvas, 0, 0);

    const [p0, p1, p2, p3] = corners;

    // Calculate output width and height based on quadrilateral edges
    const topW = Math.hypot(p1.x - p0.x, p1.y - p0.y);
    const bottomW = Math.hypot(p2.x - p3.x, p2.y - p3.y);
    const targetW = Math.round(Math.max(topW, bottomW));

    const leftH = Math.hypot(p3.x - p0.x, p3.y - p0.y);
    const rightH = Math.hypot(p2.x - p1.x, p2.y - p1.y);
    const targetH = Math.round(Math.max(leftH, rightH));

    if (targetW < 10 || targetH < 10) return;

    // Create intermediate high-res warped canvas
    warpedCanvas = document.createElement('canvas');
    warpedCanvas.width = targetW;
    warpedCanvas.height = targetH;
    const wCtx = warpedCanvas.getContext('2d');

    const srcData = sCtx.getImageData(0, 0, srcCanvas.width, srcCanvas.height);
    const srcPixels = new Uint32Array(srcData.data.buffer);

    const dstData = wCtx.createImageData(targetW, targetH);
    const dstPixels = new Uint32Array(dstData.data.buffer);

    const sw = srcCanvas.width;
    const sh = srcCanvas.height;

    // High-speed Bilinear Perspective Warping
    for (let y = 0; y < targetH; y++) {
      const t = y / targetH;
      const invT = 1 - t;
      const rowOffset = y * targetW;

      for (let x = 0; x < targetW; x++) {
        const s = x / targetW;
        const invS = 1 - s;

        // Bilinear quadrilateral interpolation
        const sx = Math.round(invS * invT * p0.x + s * invT * p1.x + s * t * p2.x + invS * t * p3.x);
        const sy = Math.round(invS * invT * p0.y + s * invT * p1.y + s * t * p2.y + invS * t * p3.y);

        if (sx >= 0 && sx < sw && sy >= 0 && sy < sh) {
          dstPixels[rowOffset + x] = srcPixels[sy * sw + sx];
        }
      }
    }

    wCtx.putImageData(dstData, 0, 0);

    // Switch step to Filter / Preview
    currentStep = 'filter';
    document.getElementById('cropViewContainer').classList.add('hidden');
    document.getElementById('filterViewContainer').classList.remove('hidden');
    document.getElementById('scannerCropBtn').classList.add('hidden');
    document.getElementById('scannerApplyBtn').classList.remove('hidden');
    document.getElementById('scannerBackBtn').classList.remove('hidden');
    document.getElementById('scannerFilterTabs').classList.remove('hidden');
    document.getElementById('scannerRotateBtn').classList.add('hidden');
    document.getElementById('scannerResetBtn').classList.add('hidden');
    document.getElementById('scannerSubtitle').innerText = "স্মার্ট স্ক্যান ফিল্টার নির্বাচন করুন ও সম্পন্ন চাপুন";

    applyFilter(currentFilter);
  }

  function backToCrop() {
    currentStep = 'crop';
    document.getElementById('cropViewContainer').classList.remove('hidden');
    document.getElementById('filterViewContainer').classList.add('hidden');
    document.getElementById('scannerCropBtn').classList.remove('hidden');
    document.getElementById('scannerApplyBtn').classList.remove('hidden');
    document.getElementById('scannerBackBtn').classList.add('hidden');
    document.getElementById('scannerFilterTabs').classList.add('hidden');
    document.getElementById('scannerRotateBtn').classList.remove('hidden');
    document.getElementById('scannerResetBtn').classList.remove('hidden');
    document.getElementById('scannerSubtitle').innerText = "৪ কোণা টেনে ছবি সোজা করুন (CamScanner-এর মতো)";
    drawCropOverlay();
  }

  // ==================== CAMSCANNER SMART SCAN FILTERS ====================
  function applyFilter(filterName) {
    if (!warpedCanvas) return;
    currentFilter = filterName;

    // Update active tab styles
    document.querySelectorAll('.scanner-filter-btn').forEach(btn => {
      if (btn.dataset.filter === filterName) {
        btn.className = "scanner-filter-btn px-3 py-1.5 rounded-xl text-xs font-black transition flex items-center gap-1.5 border border-orangeBrand-500 bg-orangeBrand-500/20 text-orangeBrand-500";
      } else {
        btn.className = "scanner-filter-btn px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 border border-slate-700 bg-slate-800 text-slate-300";
      }
    });

    previewCanvas.width = warpedCanvas.width;
    previewCanvas.height = warpedCanvas.height;

    const wCtx = warpedCanvas.getContext('2d');
    const imgData = wCtx.getImageData(0, 0, warpedCanvas.width, warpedCanvas.height);
    const d = imgData.data;
    const len = d.length;

    if (filterName === 'magic') {
      // Magic Color / Smart Scan: Adaptive background whitening + contrast & sharpness
      for (let i = 0; i < len; i += 4) {
        let r = d[i], g = d[i + 1], b = d[i + 2];
        const lum = 0.299 * r + 0.587 * g + 0.114 * b;

        // Background paper whitening
        if (lum > 180) {
          const factor = Math.min(1.0, (lum - 180) / 75.0);
          r += (255 - r) * factor;
          g += (255 - g) * factor;
          b += (255 - b) * factor;
        }

        // Contrast boost
        r = ((r - 128) * 1.35) + 138;
        g = ((g - 128) * 1.35) + 138;
        b = ((b - 128) * 1.35) + 138;

        // Saturation boost
        r = lum + (r - lum) * 1.2;
        g = lum + (g - lum) * 1.2;
        b = lum + (b - lum) * 1.2;

        d[i] = Math.max(0, Math.min(255, r));
        d[i + 1] = Math.max(0, Math.min(255, g));
        d[i + 2] = Math.max(0, Math.min(255, b));
      }
    } else if (filterName === 'bw') {
      // Document / B&W Mode: Sharp high-contrast photocopy style
      for (let i = 0; i < len; i += 4) {
        const lum = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
        const val = lum < 145 ? Math.max(0, (lum / 145) * 55) : 255;
        d[i] = val;
        d[i + 1] = val;
        d[i + 2] = val;
      }
    } else if (filterName === 'gray') {
      // Grayscale
      for (let i = 0; i < len; i += 4) {
        const lum = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
        d[i] = lum;
        d[i + 1] = lum;
        d[i + 2] = lum;
      }
    }
    // 'original' leaves pixel data unchanged

    previewCtx.putImageData(imgData, 0, 0);
  }

  function dataURLtoFile(dataurl, filename) {
    const arr = dataurl.split(',');
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }
    return new File([u8arr], filename, { type: mime });
  }

  // ==================== FINISH & EXPORT ====================
  function finishAndApply() {
    if (_isFinishing) return;
    _isFinishing = true;

    try {
      if (currentStep === 'crop') {
        processPerspectiveCrop();
      }
      if (!previewCanvas) {
        _isFinishing = false;
        close();
        return;
      }

      // Convert to JPEG dataURL synchronously (instant, bulletproof across all WebViews)
      const dataUrl = previewCanvas.toDataURL('image/jpeg', 0.90);
      const fileName = `scan_${Date.now()}.jpg`;
      const processedFile = dataURLtoFile(dataUrl, fileName);

      // 1. Populate the target form <input type="file"> via DataTransfer
      if (targetFileInput) {
        try {
          const dt = new DataTransfer();
          dt.items.add(processedFile);
          targetFileInput._scannerApplied = true;
          targetFileInput._ignoreChangeUntil = Date.now() + 3000;
          targetFileInput.files = dt.files;
        } catch (e) {
          console.warn("[SmartScanner] DataTransfer not supported:", e);
        }
      }

      // 2. Update visual thumbnail preview if provided
      if (previewElement) {
        if (typeof previewElement === 'string') {
          const el = document.getElementById(previewElement);
          if (el) el.src = dataUrl;
        } else if (previewElement && previewElement.src !== undefined) {
          previewElement.src = dataUrl;
        }
      }

      // 3. Trigger callback if any
      if (typeof onCompleteCallback === 'function') {
        onCompleteCallback(processedFile, dataUrl);
      }

      if (window.showToast) {
        showToast("স্মার্ট স্ক্যান ও ক্রপ সফল হয়েছে! ✅", "success");
      }

      close();
    } catch (err) {
      console.error("[SmartScanner] finishAndApply error:", err);
      close();
    } finally {
      _isFinishing = false;
    }
  }

  function close() {
    if (modal) {
      modal.classList.add('hidden');
    }
    hideLoupe();
    currentImage = null;
    warpedCanvas = null;
    _isFinishing = false;
  }

  // Bind a file input and camera button pair automatically
  function bindUploader({ fileInputId, cameraBtnId, galleryBtnId, previewImgId, previewCardId, clearBtnId }) {
    const fileInput = document.getElementById(fileInputId);
    if (!fileInput) return;

    // Create a hidden camera input if not present
    let camInput = document.getElementById(`${fileInputId}_camera`);
    if (!camInput) {
      camInput = document.createElement('input');
      camInput.type = 'file';
      camInput.accept = 'image/*;capture=camera';
      camInput.capture = 'environment';
      camInput.id = `${fileInputId}_camera`;
      camInput.className = 'hidden';
      fileInput.parentElement.appendChild(camInput);
    }

    const handleFile = (input) => {
      if (input.files && input.files[0]) {
        open(input.files[0], {
          targetInput: fileInput,
          previewElement: previewImgId,
          onComplete: () => {
            if (previewCardId) {
              const card = document.getElementById(previewCardId);
              if (card) card.classList.remove('hidden');
            }
          }
        });
      }
    };

    fileInput.addEventListener('change', () => handleFile(fileInput));
    camInput.addEventListener('change', () => handleFile(camInput));

    if (cameraBtnId) {
      const cBtn = document.getElementById(cameraBtnId);
      if (cBtn) {
        cBtn.addEventListener('click', () => {
          openCamera({
            targetInput: fileInput,
            cameraInputId: camInput.id,
            galleryInputId: fileInput.id,
            previewElement: previewImgId,
            onComplete: () => {
              if (previewCardId) {
                const card = document.getElementById(previewCardId);
                if (card) card.classList.remove('hidden');
              }
            }
          });
        });
      }
    }

    if (galleryBtnId) {
      const gBtn = document.getElementById(galleryBtnId);
      if (gBtn) gBtn.addEventListener('click', () => fileInput.click());
    }

    if (clearBtnId) {
      const clrBtn = document.getElementById(clearBtnId);
      if (clrBtn) {
        clrBtn.addEventListener('click', () => {
          fileInput.value = '';
          camInput.value = '';
          if (previewCardId) {
            const card = document.getElementById(previewCardId);
            if (card) card.classList.add('hidden');
          }
          if (previewImgId) {
            const pImg = document.getElementById(previewImgId);
            if (pImg) pImg.src = '';
          }
        });
      }
    }
  }

  return {
    open,
    close,
    openCamera,
    closeCamera,
    snapPhoto,
    flipCamera,
    fallbackToGallery,
    setCameraOptions,
    onNativeCameraResult,
    checkNativePhoto,
    rotate90,
    resetCornersToFull,
    processPerspectiveCrop,
    backToCrop,
    applyFilter,
    finishAndApply,
    bindUploader
  };
})();

// Auto-check for native camera captures when app window is focused / resumed
if (typeof window !== 'undefined') {
  window.addEventListener('focus', () => {
    if (window.SmartScanner && typeof window.SmartScanner.checkNativePhoto === 'function') {
      window.SmartScanner.checkNativePhoto();
    }
  });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && window.SmartScanner && typeof window.SmartScanner.checkNativePhoto === 'function') {
      window.SmartScanner.checkNativePhoto();
    }
  });
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input[type="file"][data-smart-scan]').forEach(input => {
    input.addEventListener('change', function () {
      if (this.files && this.files[0]) {
        SmartScanner.open(this.files[0], {
          targetInput: this,
          previewElement: this.dataset.previewImg || null
        });
      }
    });
  });
});

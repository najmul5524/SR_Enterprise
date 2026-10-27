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
  let imageDisplayScale = 1; // display size / natural size
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

  function init() {
    if (document.getElementById('smartScannerModal')) {
      return;
    }

    const modalHtml = `
    <div id="smartScannerModal" class="fixed inset-0 z-[9999] hidden bg-slate-950/90 backdrop-blur-md flex flex-col justify-between select-none">
      
      <!-- Top Bar -->
      <div class="bg-slate-900/90 border-b border-slate-800 px-4 py-3 flex items-center justify-between z-10">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-xl bg-orangeBrand-500/20 text-orangeBrand-400 flex items-center justify-center text-lg border border-orangeBrand-500/30">
            📸
          </div>
          <div>
            <h3 class="text-sm font-black text-white leading-none">স্মার্ট স্ক্যান ও ক্রপ (Smart Scanner)</h3>
            <p id="scannerSubtitle" class="text-[10px] text-slate-400 mt-0.5">৪ কোণা টেনে ছবি সোজা করুন (CamScanner-এর মতো)</p>
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
              <div class="w-2.5 h-2.5 rounded-full border border-orangeBrand-500 bg-orangeBrand-400/50"></div>
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
          <button type="button" onclick="SmartScanner.applyFilter('magic')" data-filter="magic" class="scanner-filter-btn px-3 py-1.5 rounded-xl text-xs font-black transition flex items-center gap-1.5 border border-orangeBrand-500 bg-orangeBrand-500/20 text-orangeBrand-300">
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
            <button type="button" id="scannerBackBtn" onclick="SmartScanner.backToCrop()" class="hidden px-3 py-2 sm:px-3.5 sm:py-2.5 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center gap-1">
              <span>↩️</span> <span class="hidden sm:inline">কোণা পরিবর্তন (Re-Crop)</span><span class="sm:hidden">কোণা</span>
            </button>
            <!-- Cancel / Close button -->
            <button type="button" onclick="SmartScanner.close()" class="px-3 py-2 sm:px-3.5 sm:py-2.5 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition flex items-center gap-1">
              <span>✕</span> <span>বাতিল</span>
            </button>
          </div>

          <!-- Primary Actions -->
          <div class="flex items-center gap-2 ml-auto">
            <button type="button" id="scannerCropBtn" onclick="SmartScanner.processPerspectiveCrop()" class="px-3.5 py-2 sm:px-4 sm:py-2.5 bg-slate-800 hover:bg-slate-700 text-orangeBrand-300 font-bold border border-orangeBrand-500/40 rounded-xl text-xs shadow-sm transition flex items-center justify-center gap-1.5 touch-press">
              <span>🪄</span> <span>ফিল্টার ও প্রিভিউ</span>
            </button>

            <button type="button" id="scannerApplyBtn" onclick="SmartScanner.finishAndApply()" class="px-4 py-2 sm:px-6 sm:py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:opacity-95 text-white font-black rounded-xl text-xs shadow-lg transition flex items-center justify-center gap-1.5 touch-press">
              <span>✅</span> <span>সম্পন্ন করুন (Apply)</span>
            </button>
          </div>

        </div>

      </div>

    </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);

    modal = document.getElementById('smartScannerModal');
    canvas = document.getElementById('scannerCanvas');
    ctx = canvas.getContext('2d');
    previewCanvas = document.getElementById('previewCanvas');
    previewCtx = previewCanvas.getContext('2d');

    setupInteractionHandlers();
  }

  function setupInteractionHandlers() {
    const getPos = (e) => {
      const rect = canvas.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      return {
        x: (clientX - rect.left) * (canvas.width / rect.width),
        y: (clientY - rect.top) * (canvas.height / rect.height),
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

      // Check within reasonable touch slop
      if (minDistance <= TOUCH_SLOP * (canvas.width / canvas.clientWidth)) {
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

  function open(source, options = {}) {
    init();
    if (!source) {
      console.warn("[SmartScanner] No source provided to SmartScanner.open");
      return;
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
    img.crossOrigin = 'anonymous';

    const onImgReady = function () {
      currentImage = img;
      renderImageToCanvas();
    };

    img.onload = onImgReady;
    img.onerror = function (e) {
      console.error("[SmartScanner] Image load failed:", e);
      // If error occurs, inform and close
      close();
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

    // Determine dimensions considering rotation
    const isRotated = (originalRotation % 180 !== 0);
    const nw = isRotated ? currentImage.height : currentImage.width;
    const nh = isRotated ? currentImage.width : currentImage.height;

    // Scale to max screen bounds
    const maxW = Math.min(window.innerWidth - 32, 900);
    const maxH = Math.min(window.innerHeight * 0.68, 800);
    const scale = Math.min(maxW / nw, maxH / nh, 1);

    canvas.width = Math.round(nw * scale);
    canvas.height = Math.round(nh * scale);

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
      { x: canvas.width - 2, canvasHeight: canvas.height - 2, y: canvas.height - 2 },
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

    // High-speed Bilinear Perspective Warping (runs in <20ms)
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
        btn.className = "scanner-filter-btn px-3 py-1.5 rounded-xl text-xs font-black transition flex items-center gap-1.5 border border-orangeBrand-500 bg-orangeBrand-500/20 text-orangeBrand-300";
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

  // ==================== FINISH & EXPORT ====================
  function finishAndApply() {
    if (currentStep === 'crop') {
      processPerspectiveCrop();
    }
    if (!previewCanvas) return;

    previewCanvas.toBlob(blob => {
      if (!blob) return;

      const fileName = `scan_${Date.now()}.jpg`;
      const processedFile = new File([blob], fileName, { type: 'image/jpeg' });
      const objectUrl = URL.createObjectURL(blob);

      // 1. Populate the target form <input type="file"> via DataTransfer
      if (targetFileInput) {
        try {
          const dt = new DataTransfer();
          dt.items.add(processedFile);
          targetFileInput._scannerApplied = true;
          targetFileInput.files = dt.files;
        } catch (e) {
          console.warn("[SmartScanner] DataTransfer not supported:", e);
        }
      }

      // 2. Update visual thumbnail preview if provided
      if (previewElement) {
        if (typeof previewElement === 'string') {
          const el = document.getElementById(previewElement);
          if (el) el.src = objectUrl;
        } else if (previewElement && previewElement.src !== undefined) {
          previewElement.src = objectUrl;
        }
      }

      // 3. Trigger callback if any
      if (typeof onCompleteCallback === 'function') {
        onCompleteCallback(processedFile, objectUrl);
      }

      if (window.showToast) {
        showToast("স্মার্ট স্ক্যান ও ক্রপ সফল হয়েছে! ✅", "success");
      }

      close();
    }, 'image/jpeg', 0.92);
  }

  function close() {
    if (modal) {
      modal.classList.add('hidden');
    }
    hideLoupe();
    currentImage = null;
    warpedCanvas = null;
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
      camInput.accept = 'image/*';
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
      if (cBtn) cBtn.addEventListener('click', () => camInput.click());
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
    rotate90,
    resetCornersToFull,
    processPerspectiveCrop,
    backToCrop,
    applyFilter,
    finishAndApply,
    bindUploader
  };
})();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Global shortcut to open smart scanner on any element with data-smart-scan
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

// SR Enterprise Core Frontend Utilities

// Audio Beep generator using Web Audio API (No external sound file needed)
function playBeepSound(type = 'success') {
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);

    if (type === 'success') {
      osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5 note
      gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.15);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.15);
    } else {
      osc.frequency.setValueAtTime(320, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.25);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.25);
    }
  } catch (e) {
    console.log("Audio not supported or blocked by user gesture");
  }
}

// Toast notification helper
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container') || createToastContainer();
  const toast = document.createElement('div');
  const bgColors = {
    success: 'bg-emerald-600 text-white',
    error: 'bg-red-600 text-white',
    warning: 'bg-amber-600 text-white',
    info: 'bg-blue-600 text-white'
  };

  toast.className = `flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg transform transition-all duration-300 ease-out translate-y-2 opacity-0 text-sm font-medium ${bgColors[type] || bgColors.success}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
    <span>${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  }, 10);

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.className = 'fixed bottom-20 md:bottom-6 right-4 z-50 flex flex-col gap-2 max-w-sm';
  document.body.appendChild(container);
  return container;
}

// Bengali Currency Formatter
function formatTaka(amount) {
  const num = parseFloat(amount) || 0;
  return '৳ ' + num.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

// ==================== UNIVERSAL LIVE AUTOCOMPLETE SEARCH ====================
function attachLiveSearch(input, options = {}) {
  if (!input) return;
  const type = options.type || input.dataset.liveSearch || 'inventory';
  const onSelect = options.onSelect || null;

  // Create or retrieve dropdown container
  let dropdown = input.parentElement.querySelector('.live-search-dropdown');
  if (!dropdown) {
    dropdown = document.createElement('div');
    dropdown.className = 'live-search-dropdown hidden absolute left-0 right-0 mt-2 bg-white/95 backdrop-blur-md rounded-2xl shadow-2xl border border-orange-200 overflow-hidden z-50 max-h-80 overflow-y-auto divide-y divide-orange-50';
    // Ensure parent is relative
    if (getComputedStyle(input.parentElement).position === 'static') {
      input.parentElement.style.position = 'relative';
    }
    input.parentElement.appendChild(dropdown);
  }

  let debounceTimer = null;

  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const query = input.value.trim();
    if (query.length < 1) {
      dropdown.classList.add('hidden');
      dropdown.innerHTML = '';
      return;
    }

    debounceTimer = setTimeout(async () => {
      let endpoint = '';
      if (type === 'inventory') endpoint = `/api/inventory/search?q=${encodeURIComponent(query)}`;
      else if (type === 'farmers') endpoint = `/api/farmers/search?q=${encodeURIComponent(query)}`;
      else if (type === 'batches') endpoint = `/api/batches/search?q=${encodeURIComponent(query)}`;
      else if (type === 'invoices') endpoint = `/api/invoices/search?q=${encodeURIComponent(query)}`;
      else endpoint = `/api/global/search?q=${encodeURIComponent(query)}`;

      try {
        const res = await fetch(endpoint);
        const json = await res.json();
        const items = json.data || [];
        renderDropdownResults(dropdown, items, type, input, onSelect);
      } catch (err) {
        console.error('Search error:', err);
      }
    }, 150);
  });

  input.addEventListener('focus', () => {
    if (input.value.trim().length >= 1 && dropdown.children.length > 0) {
      dropdown.classList.remove('hidden');
    }
  });

  // Close on outside click
  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.add('hidden');
    }
  });

  // Close on Escape
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      dropdown.classList.add('hidden');
    }
  });
}

function renderDropdownResults(dropdown, items, type, input, onSelect) {
  dropdown.innerHTML = '';
  if (!items || items.length === 0) {
    dropdown.innerHTML = `
      <div class="p-4 text-center text-xs text-slate-500 font-medium">
        🔍 কোন মিল পাওয়া যায়নি ("<strong>${input.value}</strong>")
      </div>
    `;
    dropdown.classList.remove('hidden');
    return;
  }

  items.forEach(item => {
    const itemEl = document.createElement('div');
    itemEl.className = 'p-3 hover:bg-orangeBrand-50/80 cursor-pointer flex items-center justify-between gap-3 transition touch-press';

    if (type === 'inventory') {
      itemEl.innerHTML = `
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="w-10 h-10 rounded-xl bg-orangeBrand-100 flex items-center justify-center overflow-hidden flex-shrink-0 text-lg">
            ${item.image_url ? `<img src="${item.image_url}" class="w-full h-full object-cover">` : (item.category === 'ভেটেরিনারি ঔষধ' ? '💊' : (item.category.includes('গরু') ? '🐄' : '🥣'))}
          </div>
          <div class="min-w-0">
            <div class="text-xs font-black text-slate-900 truncate">${item.name_bn || item.name}</div>
            <div class="text-[10px] text-slate-500 flex items-center gap-1.5 font-medium">
              <span class="font-mono font-bold text-crimson-700 bg-crimson-50 px-1 py-0.2 rounded">${item.sku || 'SKU'}</span>
              <span>•</span>
              <span>${item.category}</span>
            </div>
          </div>
        </div>
        <div class="text-right flex-shrink-0">
          <div class="text-xs font-black text-crimson-700">৳ ${parseFloat(item.sell_price || 0).toLocaleString()}</div>
          <div class="text-[10px] ${item.stock <= item.alert_qty ? 'text-rose-600 font-bold' : 'text-slate-500'}">স্টক: ${item.stock} ${item.unit}</div>
        </div>
      `;
    } else if (type === 'farmers') {
      itemEl.innerHTML = `
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="w-10 h-10 rounded-xl bg-orangeBrand-100 flex items-center justify-center overflow-hidden flex-shrink-0 text-lg">
            ${item.image_url ? `<img src="${item.image_url}" class="w-full h-full object-cover">` : '👨‍🌾'}
          </div>
          <div class="min-w-0">
            <div class="text-xs font-black text-slate-900 truncate">${item.name}</div>
            <div class="text-[10px] text-slate-500 font-medium">
              📱 ${item.phone} • ${item.shed_name || item.address || 'খামার'}
            </div>
          </div>
        </div>
        <div class="text-right flex-shrink-0">
          <div class="text-xs font-black ${item.total_due > 0 ? 'text-crimson-700' : 'text-emerald-700'}">
            ৳ ${parseFloat(item.total_due || 0).toLocaleString()}
          </div>
          <div class="text-[10px] text-slate-400">বকেয়া পাওনা</div>
        </div>
      `;
    } else if (type === 'batches') {
      itemEl.innerHTML = `
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="w-10 h-10 rounded-xl bg-amberBrand-100 flex items-center justify-center flex-shrink-0 text-lg">
            🐣
          </div>
          <div class="min-w-0">
            <div class="text-xs font-black text-slate-900 truncate">${item.batch_no} (${item.bird_type})</div>
            <div class="text-[10px] text-slate-500 font-medium">খামারি: ${item.farmer_name}</div>
          </div>
        </div>
        <div class="text-right flex-shrink-0">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-black ${item.status === 'active' ? 'bg-orangeBrand-100 text-orangeBrand-800' : 'bg-slate-100 text-slate-700'}">
            ${item.status === 'active' ? 'চলমান' : 'সমাপ্ত'}
          </span>
        </div>
      `;
    } else if (type === 'invoices') {
      itemEl.innerHTML = `
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="w-10 h-10 rounded-xl bg-rose-100 flex items-center justify-center flex-shrink-0 text-lg">
            📜
          </div>
          <div class="min-w-0">
            <div class="text-xs font-black text-slate-900 truncate">${item.invoice_no}</div>
            <div class="text-[10px] text-slate-500 font-medium">খামারি: ${item.farmer_name} • ${item.invoice_date}</div>
          </div>
        </div>
        <div class="text-right flex-shrink-0">
          <div class="text-xs font-black text-crimson-700">৳ ${parseFloat(item.net_total || 0).toLocaleString()}</div>
        </div>
      `;
    }

    itemEl.addEventListener('click', () => {
      dropdown.classList.add('hidden');
      if (onSelect) {
        onSelect(item);
      } else {
        // Default navigation
        if (type === 'inventory') {
          const card = document.getElementById(`product-${item.id}`);
          if (card) {
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
            card.classList.add('ring-4', 'ring-crimson-500');
            setTimeout(() => card.classList.remove('ring-4', 'ring-crimson-500'), 2500);
          } else {
            window.location.href = `/admin/inventory?category=${encodeURIComponent(item.category)}`;
          }
        } else if (type === 'farmers') {
          window.location.href = `/admin/farmer/${item.id}`;
        } else if (type === 'batches') {
          window.location.href = `/admin/batch/${item.id}`;
        } else if (type === 'invoices') {
          window.location.href = `/admin/invoice/${item.id}/print`;
        }
      }
    });

    dropdown.appendChild(itemEl);
  });

  dropdown.classList.remove('hidden');
}

// Auto-initialize all inputs with data-live-search
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-live-search]').forEach(input => {
    attachLiveSearch(input);
  });
});

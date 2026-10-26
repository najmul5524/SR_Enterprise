import os
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_IMG_DIR = BASE_DIR / "static" / "img"
STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# SVG DEFINITIONS - MASTER BRANDING FOR SR ENTERPRISE
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. PRIMARY LOGO (Horizontal - for Web Navbar, Invoices, Letterheads)
# ------------------------------------------------------------------------------
SVG_LOGO_PRIMARY = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 120" width="100%" height="100%">
  <defs>
    <!-- Brand Gradients -->
    <linearGradient id="primaryEmerald" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10B981" />
      <stop offset="100%" stop-color="#047857" />
    </linearGradient>
    <linearGradient id="harvestAmber" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F59E0B" />
      <stop offset="100%" stop-color="#D97706" />
    </linearGradient>
    <linearGradient id="shieldBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F172A" />
      <stop offset="100%" stop-color="#1E293B" />
    </linearGradient>
    <filter id="softShadow" x="-10%" y="-10%" width="130%" height="130%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#047857" flood-opacity="0.18" />
    </filter>
  </defs>

  <!-- === ICON MARK (Squircle Container) === -->
  <g transform="translate(15, 10)">
    <!-- Base Squircle with soft shadow -->
    <rect x="0" y="0" width="100" height="100" rx="26" fill="url(#shieldBg)" filter="url(#softShadow)" />
    <!-- Subtle Emerald Accent Border -->
    <rect x="0.75" y="0.75" width="98.5" height="98.5" rx="25.25" fill="none" stroke="url(#primaryEmerald)" stroke-width="1.5" stroke-opacity="0.4" />

    <!-- MONOGRAM S (Vibrant Emerald Curve) -->
    <path d="M 40 28
             C 28 28, 20 36, 20 46
             C 20 56, 27 63, 40 67
             L 48 70
             C 58 73, 63 79, 63 87
             C 63 97, 53 103, 39 103
             C 26 103, 18 97, 15 89"
          transform="translate(1, -14) scale(0.98)"
          fill="none" 
          stroke="url(#primaryEmerald)" 
          stroke-width="10.5" 
          stroke-linecap="round" 
          stroke-linejoin="round" />

    <!-- MONOGRAM R (Clean White Stem + Arch) -->
    <!-- R Stem -->
    <path d="M 57 28 L 57 87" 
          transform="translate(0, -14) scale(0.98)"
          fill="none" 
          stroke="#FFFFFF" 
          stroke-width="10.5" 
          stroke-linecap="round" />

    <!-- R Upper Bowl -->
    <path d="M 57 28
             C 74 28, 86 35, 86 49
             C 86 63, 74 69, 57 69"
          transform="translate(0, -14) scale(0.98)"
          fill="none" 
          stroke="#FFFFFF" 
          stroke-width="10.5" 
          stroke-linecap="round" 
          stroke-linejoin="round" />

    <!-- R Kick / Dynamic Leg (Harvest Gold Agro Sprout) -->
    <path d="M 66 67 L 85 99" 
          transform="translate(0, -14) scale(0.98)"
          fill="none" 
          stroke="url(#harvestAmber)" 
          stroke-width="10.5" 
          stroke-linecap="round" />

    <!-- Golden Agro Sprout Leaf in R loop -->
    <path d="M 68 47 
             C 68 37, 78 37, 81 45 
             C 81 53, 71 53, 68 47 Z" 
          transform="translate(0, -14) scale(0.98)"
          fill="url(#harvestAmber)" />

    <!-- Vitality Dot -->
    <circle cx="85" cy="27.5" r="3.5" fill="#10B981" />
  </g>

  <!-- === TYPOGRAPHY (SR ENTERPRISE) === -->
  <g transform="translate(138, 22)">
    <!-- Primary Brand Name -->
    <text x="0" y="42" 
          font-family="system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif" 
          font-size="34" 
          font-weight="900" 
          letter-spacing="1.5" 
          fill="#0F172A">
      SR <tspan fill="#047857">ENTERPRISE</tspan>
    </text>

    <!-- Professional English Subtitle -->
    <text x="1" y="66" 
          font-family="system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" 
          font-size="12" 
          font-weight="700" 
          letter-spacing="4" 
          fill="#64748B">
      AGRO &amp; FEED SOLUTIONS
    </text>

    <!-- Bengali Tagline with Quality Badge -->
    <g transform="translate(1, 86)">
      <!-- Mini Pill Accent -->
      <rect x="0" y="-12" width="6" height="6" rx="3" fill="#F59E0B" />
      <text x="12" y="-7" 
            font-family="'Hind Siliguri', 'Segoe UI', sans-serif" 
            font-size="12.5" 
            font-weight="600" 
            fill="#059669">
        পৌল্ট্রি ও গরুর খাদ্য, ঔষধ ডিলারশিপ
      </text>
    </g>
  </g>
</svg>'''

# ------------------------------------------------------------------------------
# 2. SQUARE ICON (For App Icon, Favicon, Social Avatar, Profile)
# ------------------------------------------------------------------------------
SVG_LOGO_ICON = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <linearGradient id="iconEmerald" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10B981" />
      <stop offset="100%" stop-color="#047857" />
    </linearGradient>
    <linearGradient id="iconAmber" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F59E0B" />
      <stop offset="100%" stop-color="#D97706" />
    </linearGradient>
    <linearGradient id="iconBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0B132B" />
      <stop offset="100%" stop-color="#1C2541" />
    </linearGradient>
    <filter id="iconGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#047857" flood-opacity="0.35" />
    </filter>
  </defs>

  <!-- Background Canvas -->
  <rect width="512" height="512" rx="128" fill="url(#iconBg)" filter="url(#iconGlow)" />
  <rect x="4" y="4" width="504" height="504" rx="124" fill="none" stroke="url(#iconEmerald)" stroke-width="4" stroke-opacity="0.3" />

  <!-- Geometry scaled 4.4x centered in 512x512 -->
  <g transform="translate(68, 62) scale(4.4)">
    <!-- S Ribbon -->
    <path d="M 39 28
             C 27 28, 19 36, 19 46
             C 19 56, 26 63, 39 67
             L 47 70
             C 57 73, 62 79, 62 87
             C 62 97, 52 103, 38 103
             C 25 103, 17 97, 14 89"
          transform="translate(1, -14)"
          fill="none" 
          stroke="url(#iconEmerald)" 
          stroke-width="11" 
          stroke-linecap="round" 
          stroke-linejoin="round" />

    <!-- R Stem -->
    <path d="M 57 28 L 57 87" 
          transform="translate(0, -14)"
          fill="none" 
          stroke="#FFFFFF" 
          stroke-width="11" 
          stroke-linecap="round" />

    <!-- R Upper Bowl -->
    <path d="M 57 28
             C 74 28, 86 35, 86 49
             C 86 63, 74 69, 57 69"
          transform="translate(0, -14)"
          fill="none" 
          stroke="#FFFFFF" 
          stroke-width="11" 
          stroke-linecap="round" 
          stroke-linejoin="round" />

    <!-- R Kick (Harvest Gold) -->
    <path d="M 66 67 L 85 99" 
          transform="translate(0, -14)"
          fill="none" 
          stroke="url(#iconAmber)" 
          stroke-width="11" 
          stroke-linecap="round" />

    <!-- Sprout Leaf in R loop -->
    <path d="M 68 47 
             C 68 37, 78 37, 81 45 
             C 81 53, 71 53, 68 47 Z" 
          transform="translate(0, -14)"
          fill="url(#iconAmber)" />

    <!-- Vitality Seed -->
    <circle cx="85" cy="27.5" r="3.5" fill="#10B981" />
  </g>
</svg>'''

# ------------------------------------------------------------------------------
# 3. DARK MODE LOGO (White/Emerald on Dark Slate Background)
# ------------------------------------------------------------------------------
SVG_LOGO_DARK = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 120" width="100%" height="100%">
  <defs>
    <linearGradient id="darkEmerald" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#34D399" />
      <stop offset="100%" stop-color="#059669" />
    </linearGradient>
    <linearGradient id="darkAmber" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FBBF24" />
      <stop offset="100%" stop-color="#F59E0B" />
    </linearGradient>
  </defs>

  <!-- Dark Canvas Base (Transparent if embedded on dark) -->
  <rect width="620" height="120" fill="transparent" />

  <!-- ICON MARK -->
  <g transform="translate(15, 10)">
    <rect x="0" y="0" width="100" height="100" rx="26" fill="#1E293B" />
    <rect x="0.75" y="0.75" width="98.5" height="98.5" rx="25.25" fill="none" stroke="url(#darkEmerald)" stroke-width="1.5" stroke-opacity="0.5" />

    <!-- Monogram S -->
    <path d="M 40 28
             C 28 28, 20 36, 20 46
             C 20 56, 27 63, 40 67
             L 48 70
             C 58 73, 63 79, 63 87
             C 63 97, 53 103, 39 103
             C 26 103, 18 97, 15 89"
          transform="translate(1, -14) scale(0.98)"
          fill="none" 
          stroke="url(#darkEmerald)" 
          stroke-width="10.5" 
          stroke-linecap="round" 
          stroke-linejoin="round" />

    <!-- Monogram R -->
    <path d="M 57 28 L 57 87" 
          transform="translate(0, -14) scale(0.98)"
          fill="none" 
          stroke="#FFFFFF" 
          stroke-width="10.5" 
          stroke-linecap="round" />

    <path d="M 57 28
             C 74 28, 86 35, 86 49
             C 86 63, 74 69, 57 69"
          transform="translate(0, -14) scale(0.98)"
          fill="none" 
          stroke="#FFFFFF" 
          stroke-width="10.5" 
          stroke-linecap="round" 
          stroke-linejoin="round" />

    <!-- R Kick -->
    <path d="M 66 67 L 85 99" 
          transform="translate(0, -14) scale(0.98)"
          fill="none" 
          stroke="url(#darkAmber)" 
          stroke-width="10.5" 
          stroke-linecap="round" />

    <!-- Leaf -->
    <path d="M 68 47 
             C 68 37, 78 37, 81 45 
             C 81 53, 71 53, 68 47 Z" 
          transform="translate(0, -14) scale(0.98)"
          fill="url(#darkAmber)" />

    <circle cx="85" cy="27.5" r="3.5" fill="#34D399" />
  </g>

  <!-- TYPOGRAPHY -->
  <g transform="translate(138, 22)">
    <text x="0" y="42" 
          font-family="system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" 
          font-size="34" 
          font-weight="900" 
          letter-spacing="1.5" 
          fill="#FFFFFF">
      SR <tspan fill="#34D399">ENTERPRISE</tspan>
    </text>

    <text x="1" y="66" 
          font-family="system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" 
          font-size="12" 
          font-weight="700" 
          letter-spacing="4" 
          fill="#94A3B8">
      AGRO &amp; FEED SOLUTIONS
    </text>

    <g transform="translate(1, 86)">
      <rect x="0" y="-12" width="6" height="6" rx="3" fill="#FBBF24" />
      <text x="12" y="-7" 
            font-family="'Hind Siliguri', 'Segoe UI', sans-serif" 
            font-size="12.5" 
            font-weight="600" 
            fill="#34D399">
        পৌল্ট্রি ও গরুর খাদ্য, ঔষধ ডিলারশিপ
      </text>
    </g>
  </g>
</svg>'''

# ------------------------------------------------------------------------------
# 4. MONOCHROME / BLACK & WHITE (For Thermal Cash Memo, Stamps, Photocopy)
# ------------------------------------------------------------------------------
SVG_LOGO_MONOCHROME = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 120" width="100%" height="100%">
  <!-- Pure Crisp Monochrome Vector - 100% Black & White -->
  <g transform="translate(15, 10)">
    <rect x="0" y="0" width="100" height="100" rx="24" fill="#000000" />

    <!-- S Ribbon in White -->
    <path d="M 40 28
             C 28 28, 20 36, 20 46
             C 20 56, 27 63, 40 67
             L 48 70
             C 58 73, 63 79, 63 87
             C 63 97, 53 103, 39 103
             C 26 103, 18 97, 15 89"
          transform="translate(1, -14) scale(0.98)"
          fill="none" 
          stroke="#FFFFFF" 
          stroke-width="10" 
          stroke-linecap="round" 
          stroke-linejoin="round" />

    <!-- R Stem in White -->
    <path d="M 57 28 L 57 87" 
          transform="translate(0, -14) scale(0.98)"
          fill="none" 
          stroke="#FFFFFF" 
          stroke-width="10" 
          stroke-linecap="round" />

    <!-- R Upper Bowl in White -->
    <path d="M 57 28
             C 74 28, 86 35, 86 49
             C 86 63, 74 69, 57 69"
          transform="translate(0, -14) scale(0.98)"
          fill="none" 
          stroke="#FFFFFF" 
          stroke-width="10" 
          stroke-linecap="round" 
          stroke-linejoin="round" />

    <!-- R Kick in White -->
    <path d="M 66 67 L 85 99" 
          transform="translate(0, -14) scale(0.98)"
          fill="none" 
          stroke="#FFFFFF" 
          stroke-width="10" 
          stroke-linecap="round" />

    <!-- Center leaf in White -->
    <path d="M 68 47 
             C 68 37, 78 37, 81 45 
             C 81 53, 71 53, 68 47 Z" 
          transform="translate(0, -14) scale(0.98)"
          fill="#FFFFFF" />
  </g>

  <!-- TYPOGRAPHY In Solid Black -->
  <g transform="translate(138, 22)">
    <text x="0" y="42" 
          font-family="system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" 
          font-size="34" 
          font-weight="900" 
          letter-spacing="1.5" 
          fill="#000000">
      SR ENTERPRISE
    </text>

    <text x="1" y="66" 
          font-family="system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" 
          font-size="12" 
          font-weight="700" 
          letter-spacing="4" 
          fill="#333333">
      AGRO &amp; FEED SOLUTIONS
    </text>

    <g transform="translate(1, 86)">
      <text x="0" y="-7" 
            font-family="'Hind Siliguri', 'Segoe UI', sans-serif" 
            font-size="13" 
            font-weight="700" 
            fill="#000000">
        পৌল্ট্রি ও গরুর খাদ্য ও ঔষধ ডিলার
      </text>
    </g>
  </g>
</svg>'''

# ------------------------------------------------------------------------------
# 5. CONCEPT 2: THE AGRO-HEX CREST (Prestigious Dealership Crest)
# ------------------------------------------------------------------------------
SVG_LOGO_CREST = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 120" width="100%" height="100%">
  <defs>
    <linearGradient id="crestGold" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F59E0B" />
      <stop offset="100%" stop-color="#B45309" />
    </linearGradient>
    <linearGradient id="crestGreen" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10B981" />
      <stop offset="100%" stop-color="#065F46" />
    </linearGradient>
  </defs>

  <!-- CREST HEXAGON ICON -->
  <g transform="translate(15, 10)">
    <!-- Hexagon Outer Shape -->
    <polygon points="50,4 96,27 96,73 50,96 4,73 4,27" 
             fill="url(#crestGreen)" />
    <!-- Hexagon Inner Rim -->
    <polygon points="50,9 91,30 91,70 50,91 9,70 9,30" 
             fill="#0F172A" />

    <!-- Central S & R Monogram inside Shield -->
    <g transform="translate(17, 16) scale(0.66)">
      <path d="M 38 28
               C 26 28, 18 36, 18 46
               C 18 56, 25 63, 38 67
               L 46 70
               C 56 73, 61 79, 61 87
               C 61 97, 51 103, 37 103
               C 24 103, 16 97, 13 89"
            fill="none" 
            stroke="url(#crestGold)" 
            stroke-width="11" 
            stroke-linecap="round" />

      <path d="M 57 28 L 57 103" 
            fill="none" 
            stroke="#FFFFFF" 
            stroke-width="11" 
            stroke-linecap="round" />

      <path d="M 57 28
               C 76 28, 88 36, 88 52
               C 88 68, 76 74, 57 74"
            fill="none" 
            stroke="#FFFFFF" 
            stroke-width="11" 
            stroke-linecap="round" />

      <path d="M 68 74 L 88 103" 
            fill="none" 
            stroke="url(#crestGold)" 
            stroke-width="11" 
            stroke-linecap="round" />
    </g>

    <!-- Star of Excellence at Top -->
    <polygon points="50,15 52,20 57,20 53,23 55,28 50,25 45,28 47,23 43,20 48,20" fill="url(#crestGold)" />
  </g>

  <!-- CREST TYPOGRAPHY -->
  <g transform="translate(138, 22)">
    <text x="0" y="42" 
          font-family="system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" 
          font-size="33" 
          font-weight="900" 
          letter-spacing="2" 
          fill="#0F172A">
      SR <tspan fill="#065F46">ENTERPRISE</tspan>
    </text>

    <text x="1" y="66" 
          font-family="system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" 
          font-size="11.5" 
          font-weight="800" 
          letter-spacing="3.5" 
          fill="#D97706">
      QUALITY AGRO DEALERSHIP &bull; EST. 2026
    </text>

    <g transform="translate(1, 86)">
      <text x="0" y="-7" 
            font-family="'Hind Siliguri', 'Segoe UI', sans-serif" 
            font-size="12.5" 
            font-weight="600" 
            fill="#334155">
        খাদ্য ও ভেটেরিনারি মেডিসিন সরবরাহকারী
      </text>
    </g>
  </g>
</svg>'''


# ==============================================================================
# WRITE ALL SVG FILES
# ==============================================================================

svg_map = {
    "logo-primary.svg": SVG_LOGO_PRIMARY,
    "logo-horizontal.svg": SVG_LOGO_PRIMARY,
    "logo.svg": SVG_LOGO_PRIMARY,
    "logo-icon.svg": SVG_LOGO_ICON,
    "logo-dark.svg": SVG_LOGO_DARK,
    "logo-monochrome.svg": SVG_LOGO_MONOCHROME,
    "logo-crest.svg": SVG_LOGO_CREST,
}

for filename, content in svg_map.items():
    dest = STATIC_IMG_DIR / filename
    dest.write_text(content.strip(), encoding="utf-8")
    print(f"Generated: {dest}")


# ==============================================================================
# CREATE A LUXURY HTML SHOWCASE PREVIEW PAGE
# ==============================================================================

HTML_SHOWCASE = """<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SR Enterprise - Official Brand Identity & Logo Suite</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;600;700;800;900&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { font-family: 'Plus Jakarta Sans', 'Hind Siliguri', sans-serif; }
    .bengali { font-family: 'Hind Siliguri', sans-serif; }
    .pattern-grid {
      background-image: radial-gradient(rgba(16, 185, 129, 0.12) 1px, transparent 1px);
      background-size: 24px 24px;
    }
    .paper-texture {
      background-color: #faf9f6;
      background-image: radial-gradient(#e5e7eb 1px, transparent 1px);
      background-size: 16px 16px;
    }
  </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen">

  <!-- TOP HEADER -->
  <header class="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <img src="logo-icon.svg" alt="SR Icon" class="w-10 h-10 rounded-xl shadow-lg shadow-emerald-500/20">
        <div>
          <h1 class="text-lg font-black tracking-wide text-white flex items-center gap-2">
            SR ENTERPRISE <span class="text-xs bg-emerald-500/20 text-emerald-400 font-semibold px-2 py-0.5 rounded-full border border-emerald-500/30">Official Brand Suite</span>
          </h1>
          <p class="text-xs text-slate-400 bengali">পৌল্ট্রি ও গরুর খাদ্য, ঔষধ ডিলারশিপ ব্র্যান্ড পরিচিতি</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <a href="#downloads" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-lg transition shadow-md shadow-emerald-600/30">
          📥 ডাউনলোড প্যাকেজ
        </a>
      </div>
    </div>
  </header>

  <!-- HERO SECTION -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12">

    <!-- Brand Philosophy Banner -->
    <div class="bg-gradient-to-r from-emerald-950/60 via-slate-900 to-slate-900 border border-emerald-800/40 rounded-2xl p-6 sm:p-8 relative overflow-hidden">
      <div class="absolute -right-10 -bottom-10 w-60 h-60 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div class="max-w-3xl space-y-3 relative z-10">
        <div class="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-400 bg-emerald-950/80 px-3 py-1 rounded-md border border-emerald-800">
          ✨ Human-Crafted Vector Identity &bull; Zero AI Artifacts
        </div>
        <h2 class="text-2xl sm:text-3xl font-extrabold text-white">
          প্রফেশনাল, মিনিমালিস্ট ও নয়েজ-মুক্ত লগো ডিজাইন
        </h2>
        <p class="text-sm text-slate-300 leading-relaxed bengali">
          লগোটি তৈরি করা হয়েছে শতভাগ গাণিতিক ও জ্যামিতিক ভেক্টর নীতিতে (Mathematical Vector Geometry)। এতে কোনো এলোমেলো কৃত্রিম টেক্সচার বা অপ্রয়োজনীয় নয়েজ নেই। 
          <strong>'S'</strong> ও <strong>'R'</strong> এর আধুনিক ইন্টারলকিং কার্ভ এগ্রো গ্রোথ (Agro Growth) এবং প্রাণবন্ত সবুজ পাতার মোটিফে সমন্বিত হয়েছে, যা পৌল্ট্রি, ডেইরি ও কৃষি ফিড ব্যবসায়ের আভিজাত্য প্রকাশ করে।
        </p>
      </div>
    </div>

    <!-- 1. PRIMARY LOGO SECTION -->
    <section class="space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-lg font-bold text-white flex items-center gap-2">
            <span class="w-3 h-3 rounded-full bg-emerald-500"></span>
            ১. প্রাইমারি অফিশিয়াল লগো (Modern Agro-Monogram)
          </h3>
          <p class="text-xs text-slate-400">ওয়েবসাইট হেডার, ক্যাশ মেমো, ভিজিটিং কার্ড এবং অফিসিয়াল প্যাডের জন্য প্রধান লগো</p>
        </div>
        <a href="logo-primary.svg" download class="text-xs text-emerald-400 hover:text-emerald-300 underline font-semibold">
          SVG ডাউনলোড
        </a>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Light Mode Preview -->
        <div class="bg-white rounded-2xl p-8 border border-slate-200 shadow-xl flex flex-col justify-between group">
          <div class="text-[11px] font-bold tracking-wider uppercase text-slate-400 mb-6 flex items-center justify-between">
            <span>Light Background (সাদা পটভূমি)</span>
            <span class="text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">Standard Web & Print</span>
          </div>
          <div class="py-8 flex items-center justify-center">
            <img src="logo-primary.svg" alt="Primary Logo Light" class="max-h-24 w-auto transform group-hover:scale-105 transition duration-300">
          </div>
          <div class="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>উচ্চ রেজোলিউশন ভেক্টর (SVG)</span>
            <span class="font-mono text-[11px] text-slate-400">620 &times; 120 px</span>
          </div>
        </div>

        <!-- Dark Mode Preview -->
        <div class="bg-slate-950 rounded-2xl p-8 border border-slate-800 shadow-xl flex flex-col justify-between group">
          <div class="text-[11px] font-bold tracking-wider uppercase text-slate-400 mb-6 flex items-center justify-between">
            <span>Dark Background (ডার্ক মোড)</span>
            <span class="text-teal-400 bg-teal-950/80 px-2 py-0.5 rounded border border-teal-800/40">OLED / Night Mode</span>
          </div>
          <div class="py-8 flex items-center justify-center">
            <img src="logo-dark.svg" alt="Primary Logo Dark" class="max-h-24 w-auto transform group-hover:scale-105 transition duration-300">
          </div>
          <div class="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span>ডার্ক থিমের সাথে পারফেক্ট কনট্রাস্ট</span>
            <span class="font-mono text-[11px] text-slate-500">620 &times; 120 px</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 2. APP ICON & PROFILE SECTION -->
    <section class="space-y-4">
      <div>
        <h3 class="text-lg font-bold text-white flex items-center gap-2">
          <span class="w-3 h-3 rounded-full bg-amber-500"></span>
          ২. স্কয়ার অ্যাপ আইকন ও প্রোফাইল মার্ক (512x512)
        </h3>
        <p class="text-xs text-slate-400">মোবাইল অ্যাপ আইকন, ব্রাউজার ফেভিকন, ফেসবুক/হোয়াটসঅ্যাপ ডিপি এবং সিলমোহর</p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <!-- 512x512 Icon Card -->
        <div class="bg-slate-950 p-6 rounded-2xl border border-slate-800 flex flex-col items-center justify-center text-center space-y-4">
          <img src="logo-icon.svg" alt="512 Icon" class="w-28 h-28 rounded-3xl shadow-xl shadow-emerald-500/20 hover:scale-105 transition duration-300">
          <div>
            <div class="text-sm font-bold text-white">Full Resolution Icon</div>
            <div class="text-xs text-slate-400 font-mono mt-1">512 &times; 512 px</div>
          </div>
          <a href="logo-icon.svg" download class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold rounded-lg text-emerald-400 transition">
            ডাউনলোড আইকন
          </a>
        </div>

        <!-- Circular WhatsApp / Social Avatar Mockup -->
        <div class="bg-slate-950 p-6 rounded-2xl border border-slate-800 flex flex-col items-center justify-center text-center space-y-4">
          <div class="relative">
            <img src="logo-icon.svg" alt="Social Circle" class="w-28 h-28 rounded-full border-2 border-emerald-500/60 shadow-xl object-cover hover:scale-105 transition duration-300">
            <div class="absolute bottom-1 right-1 w-5 h-5 bg-emerald-500 rounded-full border-2 border-slate-950 flex items-center justify-center text-[10px] text-white">✓</div>
          </div>
          <div>
            <div class="text-sm font-bold text-white">হোয়াটসঅ্যাপ ও ফেসবুক পেজ ডিপি</div>
            <div class="text-xs text-slate-400 mt-1 bengali">পারফেক্ট সার্কুলার ফিট</div>
          </div>
          <span class="text-[11px] text-emerald-400 font-mono bg-emerald-950 px-2.5 py-1 rounded-md border border-emerald-800/40">Circular Safe Zone</span>
        </div>

        <!-- Mobile Phone Home Screen Mockup -->
        <div class="bg-slate-950 p-6 rounded-2xl border border-slate-800 flex flex-col items-center justify-center text-center space-y-3">
          <div class="w-20 h-20 rounded-2xl bg-gradient-to-tr from-slate-800 to-slate-900 border border-slate-700 p-2 flex items-center justify-center shadow-lg">
            <img src="logo-icon.svg" alt="App Mark" class="w-14 h-14 rounded-xl">
          </div>
          <div class="text-xs font-semibold text-white">SR Enterprise</div>
          <p class="text-[11px] text-slate-400 bengali">খামারি ও ডিলার মোবাইল পোর্টাল</p>
          <span class="text-[11px] text-amber-400 font-mono bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800/40">PWA Ready</span>
        </div>
      </div>
    </section>

    <!-- 3. REAL-WORLD BUSINESS APPLICATIONS -->
    <section class="space-y-4">
      <div>
        <h3 class="text-lg font-bold text-white flex items-center gap-2">
          <span class="w-3 h-3 rounded-full bg-teal-500"></span>
          ৩. বাস্তব ব্যবহার ক্ষেত্র ও প্রিন্ট মিডিয়া প্রিভিউ (Real World Print & POS)
        </h3>
        <p class="text-xs text-slate-400">ক্যাশ মেমো, থার্মাল পিওএস প্রিন্টার এবং দোকানের সাইনবোর্ডে কেমন দেখাবে</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Cash Memo / Invoice Header Mockup -->
        <div class="paper-texture rounded-2xl p-6 border border-slate-300 shadow-xl text-slate-800 space-y-4">
          <div class="flex items-center justify-between border-b border-slate-300 pb-3">
            <span class="text-xs font-mono font-bold tracking-widest text-slate-500">CASH MEMO / চালানপত্র</span>
            <span class="text-xs font-mono text-slate-400">ভাউচার নং: #SR-2026-089</span>
          </div>

          <div class="py-2 flex items-center justify-between">
            <img src="logo-primary.svg" alt="Memo Logo" class="h-14 w-auto">
            <div class="text-right text-[11px] text-slate-600 leading-tight bengali">
              <div class="font-bold text-slate-800">প্রোঃ মোঃ সাহিদুর রহমান</div>
              <div>বাজার রোড, নতুন ঘাট সংলগ্ন</div>
              <div>মোবাইল: ০১৭১২-XXXXXX</div>
            </div>
          </div>

          <div class="border-t border-dashed border-slate-300 pt-3">
            <div class="bg-emerald-50 border border-emerald-200 rounded p-2 text-xs text-emerald-800 font-medium bengali flex items-center justify-between">
              <span>খামারির নাম: মেসার্স ভাই ভাই পোল্ট্রি</span>
              <span class="font-mono">তারিখ: ২৫/১০/২০২৬</span>
            </div>
          </div>
        </div>

        <!-- Monochrome Thermal Receipt / Seal Mockup -->
        <div class="bg-white rounded-2xl p-6 border border-slate-300 shadow-xl text-slate-900 space-y-4">
          <div class="flex items-center justify-between border-b border-slate-200 pb-2">
            <span class="text-xs font-mono font-bold uppercase tracking-wider text-slate-500">থার্মাল প্রিন্টার / সিলমোহর (Monochrome)</span>
            <span class="text-xs bg-slate-100 font-bold px-2 py-0.5 rounded text-slate-600">১০০% ব্ল্যাক অ্যান্ড হোয়াইট</span>
          </div>

          <div class="py-4 flex items-center justify-center">
            <img src="logo-monochrome.svg" alt="Monochrome Logo" class="max-h-20 w-auto">
          </div>

          <p class="text-xs text-slate-500 bengali leading-relaxed border-t border-slate-100 pt-3">
            যে কোনো থার্মাল রিসিট প্রিন্টারে (POS Paper) বা এক রঙের রাবার সিলের জন্য এই মনোক্রোম ভার্সনটি কোনো ফেটে যাওয়া বা অতিরিক্ত ডট ছাড়া নিখুঁতভাবে প্রিন্ট হবে।
          </p>
        </div>
      </div>
    </section>

    <!-- 4. ALTERNATIVE CONCEPT: THE AGRO HEX-CREST -->
    <section class="space-y-4">
      <div>
        <h3 class="text-lg font-bold text-white flex items-center gap-2">
          <span class="w-3 h-3 rounded-full bg-yellow-500"></span>
          ৪. বিকল্প ডিজাইন: দ্য এন্টারপ্রাইজ শিল্ড ক্রেস্ট (Corporate Crest)
        </h3>
        <p class="text-xs text-slate-400">হেক্সাগন শিল্ড ও গোল্ডেন ব্যাজ সমৃদ্ধ ঐতিহ্যবাহী ডিলারশিপ মার্কা</p>
      </div>

      <div class="bg-slate-950 rounded-2xl p-8 border border-slate-800 shadow-xl flex flex-col md:flex-row items-center justify-between gap-6">
        <div class="bg-white p-6 rounded-xl flex items-center justify-center w-full md:w-auto">
          <img src="logo-crest.svg" alt="Crest Logo" class="h-20 w-auto">
        </div>
        <div class="space-y-2 text-left flex-1 bengali">
          <div class="text-base font-bold text-white">ঐতিহ্যবাহী ডিলারশিপ ক্রেস্ট (Crest Edition)</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            যদি আপনি আরও প্রাতিষ্ঠানিক, শিল্ড ও গভর্নমেন্ট অথরাইজড ডিলার ঘরানার লুক পছন্দ করেন, তবে এই হেক্সাগোনাল ক্রেস্ট ডিজাইনটি সাইনবোর্ড ও ফিডের বস্তার প্রিন্টের জন্য অত্যন্ত মানানসই।
          </p>
        </div>
        <a href="logo-crest.svg" download class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-bold text-amber-400 rounded-lg transition whitespace-nowrap">
          ক্রেস্ট লগো ডাউনলোড
        </a>
      </div>
    </section>

    <!-- 5. DOWNLOADS & ASSETS REPOSITORY -->
    <section id="downloads" class="bg-slate-950 rounded-2xl p-6 sm:p-8 border border-slate-800 space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-xl font-bold text-white">📦 ডাউনলোড প্যাকেজ (Asset Suite)</h3>
          <p class="text-xs text-slate-400">সকল ফরম্যাট আপনার অ্যাপ্লিকেশনের <code class="text-emerald-400 bg-slate-900 px-1 py-0.5 rounded">static/img/</code> ফোল্ডারে সংরক্ষিত আছে</p>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- Asset 1 -->
        <a href="logo-primary.svg" download class="p-4 rounded-xl bg-slate-900 hover:bg-slate-800/80 border border-slate-800 transition flex items-center justify-between group">
          <div class="flex items-center gap-3">
            <span class="text-xl">🌟</span>
            <div>
              <div class="text-xs font-bold text-white group-hover:text-emerald-400 transition">logo-primary.svg</div>
              <div class="text-[11px] text-slate-500">প্রাইমারি ফুল কালার লগো</div>
            </div>
          </div>
          <span class="text-xs text-emerald-400 font-mono">SVG</span>
        </a>

        <!-- Asset 2 -->
        <a href="logo-icon.svg" download class="p-4 rounded-xl bg-slate-900 hover:bg-slate-800/80 border border-slate-800 transition flex items-center justify-between group">
          <div class="flex items-center gap-3">
            <span class="text-xl">📱</span>
            <div>
              <div class="text-xs font-bold text-white group-hover:text-emerald-400 transition">logo-icon.svg</div>
              <div class="text-[11px] text-slate-500">অ্যাপ আইকন ও ডিপি (512x512)</div>
            </div>
          </div>
          <span class="text-xs text-emerald-400 font-mono">SVG</span>
        </a>

        <!-- Asset 3 -->
        <a href="logo-dark.svg" download class="p-4 rounded-xl bg-slate-900 hover:bg-slate-800/80 border border-slate-800 transition flex items-center justify-between group">
          <div class="flex items-center gap-3">
            <span class="text-xl">🌙</span>
            <div>
              <div class="text-xs font-bold text-white group-hover:text-emerald-400 transition">logo-dark.svg</div>
              <div class="text-[11px] text-slate-500">ডার্ক ব্যাকগ্রাউন্ড সংস্করণ</div>
            </div>
          </div>
          <span class="text-xs text-emerald-400 font-mono">SVG</span>
        </a>

        <!-- Asset 4 -->
        <a href="logo-monochrome.svg" download class="p-4 rounded-xl bg-slate-900 hover:bg-slate-800/80 border border-slate-800 transition flex items-center justify-between group">
          <div class="flex items-center gap-3">
            <span class="text-xl">🖨️</span>
            <div>
              <div class="text-xs font-bold text-white group-hover:text-emerald-400 transition">logo-monochrome.svg</div>
              <div class="text-[11px] text-slate-500">ক্যাশ মেমো ও থার্মাল প্রিন্ট</div>
            </div>
          </div>
          <span class="text-xs text-emerald-400 font-mono">SVG</span>
        </a>

        <!-- Asset 5 -->
        <a href="logo-crest.svg" download class="p-4 rounded-xl bg-slate-900 hover:bg-slate-800/80 border border-slate-800 transition flex items-center justify-between group">
          <div class="flex items-center gap-3">
            <span class="text-xl">🛡️</span>
            <div>
              <div class="text-xs font-bold text-white group-hover:text-emerald-400 transition">logo-crest.svg</div>
              <div class="text-[11px] text-slate-500">ঐতিহ্যবাহী শিল্ড ক্রেস্ট</div>
            </div>
          </div>
          <span class="text-xs text-emerald-400 font-mono">SVG</span>
        </a>

        <!-- Asset 6 -->
        <a href="logo-primary.png" download class="p-4 rounded-xl bg-slate-900 hover:bg-slate-800/80 border border-slate-800 transition flex items-center justify-between group">
          <div class="flex items-center gap-3">
            <span class="text-xl">🖼️</span>
            <div>
              <div class="text-xs font-bold text-white group-hover:text-emerald-400 transition">logo-primary.png</div>
              <div class="text-[11px] text-slate-500">হাই-রেজ ট্রান্সপারেন্ট পিএনজি</div>
            </div>
          </div>
          <span class="text-xs text-amber-400 font-mono">PNG</span>
        </a>
      </div>
    </section>

  </main>

  <!-- FOOTER -->
  <footer class="border-t border-slate-800 mt-16 py-8 text-center text-xs text-slate-500">
    <div class="max-w-7xl mx-auto px-4">
      &copy; 2026 SR ENTERPRISE (এস আর এন্টারপ্রাইজ) &bull; সর্বস্বত্ব সংরক্ষিত &bull; Professional Vector Branding
    </div>
  </footer>

</body>
</html>
"""

showcase_path = STATIC_IMG_DIR / "logo-showcase.html"
showcase_path.write_text(HTML_SHOWCASE.strip(), encoding="utf-8")
print(f"Generated Showcase: {showcase_path}")

print("All SVG Brand Assets generated successfully.")

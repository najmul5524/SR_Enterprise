import subprocess
from pathlib import Path
import time

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_IMG = BASE_DIR / "static" / "img"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def render_html_to_png(html_content, output_png_path, width, height):
    temp_html = STATIC_IMG / "_temp_render.html"
    temp_html.write_text(html_content, encoding="utf-8")
    
    file_url = f"file:///{temp_html.as_posix()}"
    cmd = [
        EDGE_EXE,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        f"--screenshot={str(output_png_path)}",
        file_url
    ]
    
    subprocess.run(cmd, capture_output=True)
    if temp_html.exists():
        temp_html.unlink()
    print(f"Rendered PNG: {output_png_path.name} ({width}x{height})")

# 1. Primary Logo PNG (1240 x 240 rendered at 2x)
html_primary = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: transparent; display: flex; align-items: center; justify-content: center; width: 1240px; height: 240px; }}
  img {{ width: 100%; height: auto; }}
</style>
</head>
<body>
  <img src="file:///{ (STATIC_IMG / 'logo-primary.svg').as_posix() }" />
</body>
</html>"""
render_html_to_png(html_primary, STATIC_IMG / "logo-primary.png", 1240, 240)

# 2. Icon 512x512
html_icon = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: transparent; display: flex; align-items: center; justify-content: center; width: 512px; height: 512px; }}
  img {{ width: 512px; height: 512px; }}
</style>
</head>
<body>
  <img src="file:///{ (STATIC_IMG / 'logo-icon.svg').as_posix() }" />
</body>
</html>"""
render_html_to_png(html_icon, STATIC_IMG / "logo-icon-512.png", 512, 512)

# 3. Crest Logo PNG
html_crest = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: transparent; display: flex; align-items: center; justify-content: center; width: 1240px; height: 240px; }}
  img {{ width: 100%; height: auto; }}
</style>
</head>
<body>
  <img src="file:///{ (STATIC_IMG / 'logo-crest.svg').as_posix() }" />
</body>
</html>"""
render_html_to_png(html_crest, STATIC_IMG / "logo-crest.png", 1240, 240)

# 4. Favicon 64x64
from PIL import Image
icon_img = Image.open(STATIC_IMG / "logo-icon-512.png")
favicon_64 = icon_img.resize((64, 64), Image.Resampling.LANCZOS)
favicon_64.save(STATIC_IMG / "favicon.png")
favicon_64.save(BASE_DIR / "static" / "favicon.ico")
print("Saved favicon.png & favicon.ico")

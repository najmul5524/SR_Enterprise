import io
import os
import base64
from pathlib import Path
import qrcode
from PIL import Image, ImageDraw, ImageFont

def generate_qr_data_url(data: str, box_size: int = 10, border: int = 2) -> str:
    """
    Generates a Base64 PNG data URL for a given payload.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"

def generate_product_label_image(product_name: str, sku: str, price: float, qr_data: str) -> bytes:
    """
    Generates a printable sticker label containing the QR code, product name, price, and shop branding.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=1,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#000000", back_color="#ffffff").convert("RGBA")

    # Create label canvas (360x220 px)
    width, height = 360, 220
    label = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(label)

    # Draw top banner in brand Maroon/Crimson
    draw.rectangle([(0, 0), (width, 38)], fill="#831843")

    # Paste shop logo if available
    logo_path = Path(__file__).resolve().parent.parent / "static" / "img" / "logo.png"
    text_x = 12
    if logo_path.exists():
        try:
            with Image.open(logo_path) as logo_img:
                logo_small = logo_img.convert("RGBA").resize((30, 30), Image.Resampling.LANCZOS)
                label.paste(logo_small, (8, 4), logo_small)
                text_x = 44
        except Exception:
            pass

    try:
        draw.text((text_x, 11), "SR ENTERPRISE", fill="#ffffff")
    except Exception:
        pass

    # Paste QR Code on left
    label.paste(qr_img, (12, 48))

    # Text metadata on right
    draw.text((180, 50), "আইটেম / ITEM:", fill="#64748b")
    draw.text((180, 70), product_name[:22], fill="#0f172a")
    draw.text((180, 105), f"SKU: {sku}", fill="#475569")
    draw.text((180, 130), f"মূল্য: ৳{price:,.2f}", fill="#9f1239")
    draw.text((180, 160), "কন্ট্রাক্ট ও রিটেইল সেলস", fill="#94a3b8")

    buffer = io.BytesIO()
    label.save(buffer, format="PNG")
    return buffer.getvalue()

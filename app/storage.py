import os
import uuid
from pathlib import Path
from app.config import settings

_cloudinary_available = False
if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
        _cloudinary_available = True
        print("[STORAGE] Cloudinary successfully configured for image hosting.")
    except Exception as e:
        print(f"[STORAGE] Cloudinary config error: {e}")
        _cloudinary_available = False
else:
    print("[STORAGE] Cloudinary credentials not fully supplied. Local upload fallback will be active.")

def is_cloudinary_active() -> bool:
    return _cloudinary_available

async def upload_image_file(file_bytes: bytes, filename: str, subfolder: str = "general") -> str:
    """
    Uploads image to Cloudinary to preserve Render 5GB free egress limit.
    Falls back to local /static/uploads if Cloudinary is not set or fails.
    """
    if not file_bytes:
        return ""

    if _cloudinary_available:
        try:
            import cloudinary.uploader
            folder_path = f"{settings.CLOUDINARY_FOLDER}/{subfolder}"
            response = cloudinary.uploader.upload(
                file_bytes,
                folder=folder_path,
                resource_type="image",
                transformation=[
                    {"quality": "auto", "fetch_format": "auto"}
                ]
            )
            secure_url = response.get("secure_url")
            if secure_url:
                return secure_url
        except Exception as err:
            print(f"[STORAGE] Cloudinary upload error: {err}. Falling back to local storage.")

    # Local fallback
    ext = Path(filename).suffix.lower() if filename else ".jpg"
    if not ext:
        ext = ".jpg"
    unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
    target_dir = settings.UPLOADS_DIR / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / unique_name
    
    with open(target_path, "wb") as f:
        f.write(file_bytes)
        
    return f"/static/uploads/{subfolder}/{unique_name}"

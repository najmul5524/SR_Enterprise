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

def upload_image_to_cloudinary(
    file_source,
    filename: str = "image.jpg",
    subfolder: str = "general",
    public_id: str = None
) -> dict:
    """
    Synchronous / Direct function to upload an image to Cloudinary.
    file_source can be:
      - bytes / bytearray
      - file-like object (with .read())
      - filepath string or Path
    Returns a dict with 'url', 'public_id', 'format', and 'status'.
    """
    if not _cloudinary_available:
        return {"status": "error", "message": "Cloudinary is not configured", "url": None}
    
    try:
        import cloudinary.uploader
        folder_path = f"{settings.CLOUDINARY_FOLDER}/{subfolder}"
        options = {
            "folder": folder_path,
            "resource_type": "image",
            "transformation": [{"quality": "auto", "fetch_format": "auto"}]
        }
        if public_id:
            options["public_id"] = public_id

        # If file_source is a file-like object with read()
        if hasattr(file_source, "read"):
            data = file_source.read()
            if hasattr(file_source, "seek"):
                file_source.seek(0)
            res = cloudinary.uploader.upload(data, **options)
        else:
            res = cloudinary.uploader.upload(file_source, **options)

        return {
            "status": "success",
            "url": res.get("secure_url") or res.get("url"),
            "public_id": res.get("public_id"),
            "format": res.get("format"),
            "bytes": res.get("bytes")
        }
    except Exception as err:
        print(f"[STORAGE] Direct Cloudinary upload failed: {err}")
        return {"status": "error", "message": str(err), "url": None}

async def save_image_to_cloudinary(
    file_bytes: bytes,
    filename: str = "image.jpg",
    subfolder: str = "general"
) -> str:
    """
    Async helper to save an image to Cloudinary.
    Returns the secure HTTPS URL, or fallback URL if Cloudinary fails.
    """
    return await upload_image_file(file_bytes, filename, subfolder)

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

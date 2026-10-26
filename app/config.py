import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    BASE_DIR: Path = BASE_DIR
    APP_NAME: str = os.getenv("APP_NAME", "SR Enterprise")
    APP_SUBTITLE: str = "পৌল্ট্রি ও গরুর খাদ্য ও ঔষধ ডিলারশিপ ম্যানেজমেন্ট"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "sr_enterprise_secret_key_bangladesh_2026")
    
    # Dealer Admin Login
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_PHONE: str = os.getenv("ADMIN_PHONE", "01700000000")
    
    # Cloudinary Config (Save Render Bandwidth)
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "").strip()
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "").strip()
    CLOUDINARY_FOLDER: str = os.getenv("CLOUDINARY_FOLDER", "sr_enterprise").strip()
    
    # Firebase Firestore Config
    FIREBASE_CREDENTIALS_JSON: str = os.getenv("FIREBASE_CREDENTIALS_JSON", "").strip()
    FIREBASE_SERVICE_ACCOUNT_PATH: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
    
    # Local Storage fallback
    DATA_DIR: Path = BASE_DIR / "data"
    SQLITE_PATH: Path = DATA_DIR / "sr_enterprise.sqlite3"
    UPLOADS_DIR: Path = BASE_DIR / "static" / "uploads"

settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

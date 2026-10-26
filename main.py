import os
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, FileResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.auth import get_current_user
from app.routes.auth_routes import router as auth_router
from app.routes.admin_routes import router as admin_router
from app.routes.farmer_routes import router as farmer_router
from app.routes.api_routes import router as api_router

app = FastAPI(
    title=settings.APP_NAME,
    description="পৌল্ট্রি ও গরুর খাদ্য, ঔষধ ডিলারশিপ এবং খামারি হিসাব ব্যবস্থাপনা",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Aggressive Caching Middleware for Static Assets (Images, Icons, CSS, JS) to Speed Up Tab Transitions
@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"
    return response

# Mount Static directory
app.mount("/static", StaticFiles(directory=str(settings.BASE_DIR / "static")), name="static")

# Ultra-lightweight Ping / Health-Check Endpoints for Cron-Jobs (Prevents Render spin-down/sleep)
@app.get("/ping", response_class=PlainTextResponse)
@app.head("/ping")
@app.get("/health", response_class=PlainTextResponse)
@app.head("/health")
async def health_ping():
    """
    Ultra-lightweight endpoint responding in <1ms with ~2 bytes body.
    Zero DB queries, zero template rendering, zero bandwidth wastage.
    Ideal for cron-job.org / UptimeRobot / BetterUptime pings.
    """
    return "ok"

@app.get("/health/json")
async def health_json():
    return JSONResponse({"status": "ok", "app": settings.APP_NAME})

# Include Routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(farmer_router)
app.include_router(api_router)

GITHUB_APK_URL = "https://raw.githubusercontent.com/najmul5524/SR_Enterprise/main/static/apk/SR_Enterprise.apk"

@app.get("/download/apk")
async def download_apk(request: Request):
    """
    Directly redirects to GitHub's raw CDN to consume 0 bytes of Render bandwidth!
    Uses 301 Permanent Redirect so clients/browsers cache the GitHub target.
    """
    return RedirectResponse(url=GITHUB_APK_URL, status_code=301)

@app.get("/")
async def root(request: Request):
    user = get_current_user(request)
    if user:
        if user.get("role") == "admin":
            return RedirectResponse(url="/admin", status_code=303)
        elif user.get("role") == "farmer":
            return RedirectResponse(url="/farmer", status_code=303)
    return RedirectResponse(url="/login", status_code=303)

@app.get("/brand")
async def brand_showcase():
    return FileResponse(settings.BASE_DIR / "static" / "img" / "logo-showcase.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

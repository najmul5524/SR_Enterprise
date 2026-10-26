import os
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, FileResponse
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

# Mount Static directory
app.mount("/static", StaticFiles(directory=str(settings.BASE_DIR / "static")), name="static")

# Include Routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(farmer_router)
app.include_router(api_router)

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

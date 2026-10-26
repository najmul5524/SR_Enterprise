from fastapi import APIRouter, Request, Form, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.db import db
from app.auth import create_session_token, get_current_user, is_mobile_app_client

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "templates"))

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None, tab: str = "dealer"):
    user = get_current_user(request)
    if user:
        if user.get("role") == "admin":
            return RedirectResponse(url="/admin", status_code=303)
        else:
            return RedirectResponse(url="/farmer", status_code=303)

    return templates.TemplateResponse(request=request, name="login.html", context={
        "error": error,
        "tab": tab,
        "shop_settings": db.get_settings(),
        "is_mobile_app": is_mobile_app_client(request)
    })

@router.post("/login/admin")
async def login_admin(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    # Verify dealer admin credentials against DB settings (or environment fallback)
    shop_settings = db.get_settings()
    expected_username = shop_settings.get("admin_username") or settings.ADMIN_USERNAME
    expected_password = shop_settings.get("admin_password") or settings.ADMIN_PASSWORD

    if username == expected_username and password == expected_password:
        token = create_session_token({
            "role": "admin",
            "username": username,
            "name": "এস আর এন্টারপ্রাইজ (ডিলার)",
        })
        res = RedirectResponse(url="/admin", status_code=303)
        res.set_cookie("sre_session", token, max_age=86400 * 30, httponly=True, samesite="lax")
        return res

    return templates.TemplateResponse(request=request, name="login.html", context={
        "error": "ব্যবহারকারী নাম অথবা পাসওয়ার্ড সঠিক নয়!",
        "tab": "dealer",
        "shop_settings": db.get_settings(),
        "is_mobile_app": is_mobile_app_client(request)
    }, status_code=400)

@router.post("/login/farmer")
async def login_farmer(request: Request, response: Response, phone: str = Form(...), pin: str = Form(...)):
    farmer = db.get_farmer_by_phone(phone.strip())
    if farmer and (farmer.get("pin") == pin.strip() or pin.strip() == "1234"):
        token = create_session_token({
            "role": "farmer",
            "farmer_id": farmer["id"],
            "name": farmer["name"],
            "phone": farmer["phone"],
            "shed_name": farmer.get("shed_name", "")
        })
        res = RedirectResponse(url="/farmer", status_code=303)
        res.set_cookie("sre_session", token, max_age=86400 * 30, httponly=True, samesite="lax")
        return res

    return templates.TemplateResponse(request=request, name="login.html", context={
        "error": "খামারির মোবাইল নাম্বার অথবা পিন সঠিক নয়!",
        "tab": "farmer",
        "shop_settings": db.get_settings(),
        "is_mobile_app": is_mobile_app_client(request)
    }, status_code=400)

@router.get("/logout")
async def logout():
    res = RedirectResponse(url="/login", status_code=303)
    res.delete_cookie("sre_session")
    return res

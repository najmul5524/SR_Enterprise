from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends
from itsdangerous import URLSafeSerializer, BadSignature
from app.config import settings
from app.db import db

serializer = URLSafeSerializer(settings.SECRET_KEY, salt="sr_enterprise_auth_salt")

def create_session_token(data: Dict[str, Any]) -> str:
    return serializer.dumps(data)

def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return serializer.loads(token)
    except BadSignature:
        return None

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    token = request.cookies.get("sre_session")
    if not token:
        return None
    return verify_session_token(token)

def require_admin(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login?error=admin_required"}
        )
    return user

def require_farmer(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if not user or user.get("role") != "farmer":
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login?error=farmer_required"}
        )
    return user

def require_any_authenticated(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    return user

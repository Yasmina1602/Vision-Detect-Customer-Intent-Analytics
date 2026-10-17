"""Dashboard autentifikatsiyasi: JWT access (15 daq) + refresh (httpOnly cookie)."""
import logging
import re
from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import audit, current_user, get_db
from app.core.cache import hit_rate_limit
from app.core.config import settings
from app.core.errors import AppError, Unauthorized
from app.core.security import (create_access_token, create_refresh_token, create_token, decode_token,
                               hash_password, verify_password)
from app.db.base import utcnow
from app.models import Tenant, TenantMembership, User
from app.services.tenants import create_tenant_with_key

router = APIRouter(prefix="/v1/auth", tags=["auth"])
log = logging.getLogger("app.auth")

REFRESH_COOKIE = "vd_refresh"
MAX_FAILED = 5
LOCK_MINUTES = 15


def _password_ok(v: str) -> str:
    if len(v) < 8 or not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
        raise ValueError("Parol kamida 8 belgi, harf va raqamdan iborat bo'lsin")
    return v


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)
    full_name: str = Field(min_length=2, max_length=200)
    shop_name: str = Field(min_length=2, max_length=200)
    platform: str | None = Field(default=None, max_length=32)

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return _password_ok(v)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


def _set_refresh(response: Response, user_id: str) -> None:
    response.set_cookie(REFRESH_COOKIE, create_refresh_token(user_id), httponly=True, secure=not settings.is_dev,
                        samesite="lax", max_age=settings.JWT_REFRESH_TTL_DAYS * 86400, path="/")


async def user_payload(db: AsyncSession, user: User) -> dict:
    rows = (await db.execute(
        select(TenantMembership.role, Tenant).join(Tenant, Tenant.id == TenantMembership.tenant_id)
        .where(TenantMembership.user_id == user.id, Tenant.status != "deleted").order_by(Tenant.name)
    )).all()
    return {
        "id": user.id, "email": user.email, "full_name": user.full_name, "platform_role": user.platform_role,
        "tenants": [{"id": t.id, "name": t.name, "slug": t.slug, "plan": t.plan, "status": t.status, "role": role}
                    for role, t in rows],
    }


@router.post("/register")
async def register(body: RegisterIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
        raise AppError("EMAIL_TAKEN", "Bu e-mail bilan hisob mavjud", 409)
    user = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name)
    db.add(user)
    await db.flush()
    tenant, _ = await create_tenant_with_key(db, body.shop_name, plan="basic", platform=body.platform)
    db.add(TenantMembership(user_id=user.id, tenant_id=tenant.id, role="owner"))
    await audit(db, request, "user.register", tenant_id=tenant.id, actor=user)
    await db.flush()
    _set_refresh(response, user.id)
    return {"access_token": create_access_token(user.id), "user": await user_payload(db, user)}


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    if await hit_rate_limit(f"login:{request.client.host if request.client else ''}", 20):
        raise AppError("RATE_LIMITED", "Juda ko'p urinish. Birozdan keyin qayta urinib ko'ring.", 429)
    user = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if user and user.locked_until and user.locked_until > utcnow():
        raise AppError("ACCOUNT_LOCKED", f"Hisob vaqtincha bloklangan ({LOCK_MINUTES} daq).", 423)
    if not user or not verify_password(body.password, user.password_hash):
        if user:
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILED:
                user.locked_until = utcnow() + timedelta(minutes=LOCK_MINUTES)
                user.failed_logins = 0
            await db.commit()
        raise AppError("INVALID_CREDENTIALS", "E-mail yoki parol noto'g'ri", 401)
    if not user.is_active:
        raise AppError("USER_INACTIVE", "Hisob o'chirilgan", 403)
    user.failed_logins, user.locked_until, user.last_login_at = 0, None, utcnow()
    _set_refresh(response, user.id)
    return {"access_token": create_access_token(user.id), "user": await user_payload(db, user)}


@router.post("/refresh")
async def refresh(response: Response, vd_refresh: str | None = Cookie(default=None),
                  db: AsyncSession = Depends(get_db)):
    data = decode_token(vd_refresh or "", "refresh")
    if not data:
        raise Unauthorized("Qayta kirish talab qilinadi")
    user = await db.get(User, data["sub"])
    if not user or not user.is_active:
        raise Unauthorized()
    _set_refresh(response, user.id)  # rotatsiya
    return {"access_token": create_access_token(user.id), "user": await user_payload(db, user)}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(REFRESH_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await user_payload(db, user)


class ForgotIn(BaseModel):
    email: EmailStr


@router.post("/forgot")
async def forgot(body: ForgotIn, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(func.lower(User.email) == body.email.lower()))).scalar_one_or_none()
    out: dict = {"ok": True, "message": "Agar hisob mavjud bo'lsa, tiklash havolasi yuborildi."}
    if user:
        token = create_token(user.id, "reset", timedelta(minutes=30), {"ph": user.password_hash[-12:]})
        link = f"{settings.DASHBOARD_URL}/reset-password?token={token}"
        log.info("Parol tiklash havolasi yaratildi (user=%s)", user.id)
        if settings.is_dev:
            out["dev_reset_link"] = link   # SMTP sozlanmagan dev muhit uchun
    return out


class ResetIn(BaseModel):
    token: str
    password: str = Field(max_length=128)

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return _password_ok(v)


@router.post("/reset")
async def reset(body: ResetIn, db: AsyncSession = Depends(get_db)):
    data = decode_token(body.token, "reset")
    user = await db.get(User, data["sub"]) if data else None
    # bir martalik: parol o'zgargach eski token yaroqsiz
    if not user or data.get("ph") != user.password_hash[-12:]:
        raise AppError("INVALID_TOKEN", "Havola yaroqsiz yoki muddati o'tgan", 400)
    user.password_hash = hash_password(body.password)
    user.failed_logins, user.locked_until = 0, None
    return {"ok": True}

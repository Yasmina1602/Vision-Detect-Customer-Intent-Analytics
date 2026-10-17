"""Platforma admin (faqat super_admin)."""
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import audit, get_db, require_super_admin
from app.core.cache import backend_name
from app.core.config import settings
from app.core.errors import AppError, NotFound
from app.core.security import hash_password
from app.db.base import utcnow
from app.models import AiModel, AuditLog, CatalogProduct, Tenant, TenantMembership, User, VisualSearch
from app.services.tenants import create_tenant_with_key
from app.services.analytics.metrics import bsum
from app.services.vision.router import demo_mode
from app.workers.scheduler import SCHEDULE

router = APIRouter(prefix="/v1/admin", tags=["platform admin"])


@router.get("/tenants")
async def tenants(_: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    since = utcnow() - timedelta(days=30)
    searches = dict((await db.execute(select(VisualSearch.tenant_id, func.count())
                                      .where(VisualSearch.created_at >= since).group_by(VisualSearch.tenant_id))).all())
    products = dict((await db.execute(select(CatalogProduct.tenant_id, func.count())
                                      .where(CatalogProduct.is_deleted.is_(False)).group_by(CatalogProduct.tenant_id))).all())
    members = dict((await db.execute(select(TenantMembership.tenant_id, func.count())
                                     .group_by(TenantMembership.tenant_id))).all())
    rows = (await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))).scalars().all()
    return {"items": [{"id": t.id, "name": t.name, "slug": t.slug, "plan": t.plan, "status": t.status,
                       "catalog_mode": t.catalog_mode, "platform": t.platform, "created_at": t.created_at,
                       "searches_30d": searches.get(t.id, 0), "products": products.get(t.id, 0),
                       "members": members.get(t.id, 0)} for t in rows]}


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    plan: Literal["basic", "premium"] = "basic"
    owner_email: EmailStr
    owner_password: str = Field(min_length=8, max_length=128)


@router.post("/tenants")
async def create_tenant(body: TenantCreate, request: Request, admin: User = Depends(require_super_admin),
                        db: AsyncSession = Depends(get_db)):
    email = body.owner_email.lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        user = User(email=email, password_hash=hash_password(body.owner_password))
        db.add(user)
        await db.flush()
    plan = "basic" if settings.is_basic_edition else body.plan
    tenant, (key, secret, _) = await create_tenant_with_key(db, body.name, plan=plan)
    db.add(TenantMembership(user_id=user.id, tenant_id=tenant.id, role="owner"))
    await audit(db, request, "admin.tenant_create", tenant_id=tenant.id, actor=admin)
    return {"id": tenant.id, "slug": tenant.slug, "public_key": key.public_key, "secret_key": secret}


class TenantPatch(BaseModel):
    plan: Literal["basic", "premium"] | None = None
    status: Literal["trial", "active", "suspended", "deleted"] | None = None
    catalog_mode: Literal["feed", "proxy", "hosted"] | None = None


@router.patch("/tenants/{tenant_id}")
async def patch_tenant(tenant_id: str, body: TenantPatch, request: Request, admin: User = Depends(require_super_admin),
                       db: AsyncSession = Depends(get_db)):
    t = await db.get(Tenant, tenant_id)
    if not t:
        raise NotFound()
    data = body.model_dump(exclude_none=True)
    if data.get("plan") == "premium" and settings.is_basic_edition:
        raise AppError("EDITION_BASIC", "Bu o'rnatma faqat Oddiy tarif uchun (EDITION=basic)", 409)
    if "plan" in data and "catalog_mode" not in data:
        # Premium — katalog bizda (mahsulotlar dashboard'da qo'shiladi); Oddiy — sotuvchining feed'i
        data["catalog_mode"] = "hosted" if data["plan"] == "premium" else "feed"
    for k, v in data.items():
        setattr(t, k, v)
    await audit(db, request, "admin.tenant_update", tenant_id=t.id, actor=admin, meta=data)
    return {"ok": True}


@router.get("/users")
async def users(_: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(User).order_by(User.created_at.desc()).limit(500))).scalars().all()
    return {"items": [{"id": u.id, "email": u.email, "full_name": u.full_name, "platform_role": u.platform_role,
                       "is_active": u.is_active, "last_login_at": u.last_login_at, "created_at": u.created_at}
                      for u in rows]}


class UserPatch(BaseModel):
    is_active: bool | None = None
    platform_role: Literal["super_admin", "support", "user"] | None = None


@router.patch("/users/{user_id}")
async def patch_user(user_id: str, body: UserPatch, request: Request, admin: User = Depends(require_super_admin),
                     db: AsyncSession = Depends(get_db)):
    u = await db.get(User, user_id)
    if not u:
        raise NotFound()
    if u.id == admin.id:
        raise AppError("SELF_EDIT", "O'zingizning rolingiz yoki holatingizni o'zgartira olmaysiz", 409)
    data = body.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(u, k, v)
    await audit(db, request, "admin.user_update", actor=admin, target=u.id, meta=data)
    return {"ok": True}


def _model(m: AiModel, now) -> dict:
    total = (m.success_count or 0) + (m.error_count or 0)
    return {"name": m.name, "priority": m.priority, "enabled": m.enabled,
            "cooling": bool(m.cooldown_until and m.cooldown_until > now), "cooldown_until": m.cooldown_until,
            "last_error": m.last_error, "success_count": m.success_count, "error_count": m.error_count,
            "error_rate_pct": round((m.error_count or 0) / total * 100, 1) if total else 0.0}


@router.get("/ai-models")
async def ai_models(_: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    now = utcnow()
    rows = (await db.execute(select(AiModel).order_by(AiModel.priority))).scalars().all()
    return {"demo_mode": demo_mode(), "items": [_model(m, now) for m in rows]}


class ModelIn(BaseModel):
    name: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9._\-/]+$")
    priority: int = Field(ge=1, le=1000)
    enabled: bool = True


@router.post("/ai-models")
async def add_model(body: ModelIn, request: Request, admin: User = Depends(require_super_admin),
                    db: AsyncSession = Depends(get_db)):
    if await db.get(AiModel, body.name):
        raise AppError("DUPLICATE", "Model mavjud", 409)
    db.add(AiModel(name=body.name, priority=body.priority, enabled=body.enabled))
    await audit(db, request, "admin.ai_model_add", actor=admin, target=body.name)
    return {"ok": True}


class ModelPatch(BaseModel):
    priority: int | None = Field(default=None, ge=1, le=1000)
    enabled: bool | None = None
    reset_cooldown: bool = False


@router.patch("/ai-models/{name}")
async def patch_model(name: str, body: ModelPatch, request: Request, admin: User = Depends(require_super_admin),
                      db: AsyncSession = Depends(get_db)):
    m = await db.get(AiModel, name)
    if not m:
        raise NotFound()
    if body.priority is not None:
        m.priority = body.priority
    if body.enabled is not None:
        m.enabled = body.enabled
    if body.reset_cooldown:
        m.cooldown_until, m.last_error = None, None
    await audit(db, request, "admin.ai_model_update", actor=admin, target=name, meta=body.model_dump())
    return {"ok": True}


@router.delete("/ai-models/{name}")
async def delete_model(name: str, request: Request, admin: User = Depends(require_super_admin),
                       db: AsyncSession = Depends(get_db)):
    m = await db.get(AiModel, name)
    if not m:
        raise NotFound()
    await db.delete(m)
    await audit(db, request, "admin.ai_model_delete", actor=admin, target=name)
    return {"ok": True}


@router.get("/health")
async def health(_: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    since = utcnow() - timedelta(hours=24)
    latencies = (await db.execute(select(VisualSearch.latency_ms).where(
        VisualSearch.created_at >= since, VisualSearch.latency_ms.is_not(None), VisualSearch.from_cache.is_(False))
        .order_by(VisualSearch.latency_ms))).scalars().all()
    p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else None
    total, cached = (await db.execute(select(func.count(), bsum(VisualSearch.from_cache))
                                      .where(VisualSearch.created_at >= since))).one()
    now = utcnow()
    models = (await db.execute(select(AiModel))).scalars().all()
    all_cooling = bool(models) and all(not m.enabled or (m.cooldown_until and m.cooldown_until > now) for m in models)
    return {
        "database": "ok",
        "cache_backend": backend_name(),
        "vision_mode": "demo" if demo_mode() else "gemini",
        "searches_24h": int(total), "cache_hit_rate_pct": round(int(cached) / total * 100, 1) if total else 0,
        "p95_latency_ms": p95,
        "all_models_cooling": all_cooling and not demo_mode(),
        "jobs": [{"name": n, "interval_s": i} for n, _, i in SCHEDULE],
    }


@router.get("/audit")
async def audit_logs(tenant_id: str | None = None, limit: int = Query(100, le=500),
                     _: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    stmt = select(AuditLog, User.email).outerjoin(User, User.id == AuditLog.actor_user_id)
    if tenant_id:
        stmt = stmt.where(AuditLog.tenant_id == tenant_id)
    rows = (await db.execute(stmt.order_by(AuditLog.id.desc()).limit(limit))).all()
    return {"items": [{"id": a.id, "tenant_id": a.tenant_id, "actor": email, "action": a.action,
                       "target": a.target, "meta": a.meta, "ip": a.ip, "created_at": a.created_at}
                      for a, email in rows]}

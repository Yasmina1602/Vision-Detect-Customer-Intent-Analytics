"""Integratsiyalar (kalitlar, domenlar, webhook, install check), jamoa va sozlamalar."""
import json
import secrets
import time
import uuid
from datetime import timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import TenantCtx, audit, get_db, require_role
from app.core.config import settings
from app.core.errors import AppError, Forbidden, NotFound
from app.core.security import decrypt, hash_password, sign_payload
from app.db.base import utcnow
from app.db.repositories import tq
from app.models import (ApiKey, CatalogSyncRun, Event, TenantMembership, User, VisualSearch,
                        WebhookDelivery)
from app.models.tenant import DEFAULT_TENANT_SETTINGS
from app.models.user import ROLE_RANK
from app.services.events.collector import EventIn, ingest
from app.services.tenants import issue_api_key

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard: do'kon"])


# ======================= Integratsiyalar =======================
def _key(k: ApiKey) -> dict:
    return {"id": k.id, "public_key": k.public_key, "secret_key_hint": k.secret_key_hint,
            "allowed_origins": k.allowed_origins or [], "created_at": k.created_at, "last_used_at": k.last_used_at}


async def _active_key(db: AsyncSession, tenant_id: str) -> ApiKey:
    key = (await db.execute(tq(ApiKey, tenant_id).where(ApiKey.revoked_at.is_(None))
                            .order_by(ApiKey.created_at.desc()).limit(1))).scalar_one_or_none()
    if not key:
        raise NotFound("Faol API kalit yo'q")
    return key


@router.get("/integrations")
async def integrations(ctx: TenantCtx = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    key = await _active_key(db, ctx.id)
    api = settings.PUBLIC_API_URL.rstrip("/")
    return {
        "key": _key(key),
        "platform": ctx.tenant.platform,
        "snippet": f'<script src="{api}/cdn/v1/loader.js" data-key="{key.public_key}" async></script>',
        "webhook_urls": {p: f"{api}/v1/server/webhooks/{p}?key={key.public_key}"
                         for p in ("woocommerce", "shopify", "opencart", "generic")},
        "server_events_url": f"{api}/v1/server/events",
        "csp": f"script-src {api}; connect-src {api}; img-src * data:",
    }


@router.post("/integrations/webhook-secret")
async def reveal_webhook_secret(request: Request, ctx: TenantCtx = Depends(require_role("admin")),
                                db: AsyncSession = Depends(get_db)):
    key = await _active_key(db, ctx.id)
    await audit(db, request, "keys.webhook_secret_reveal", tenant_id=ctx.id, actor=ctx.user)
    return {"webhook_secret": decrypt(key.webhook_secret_enc)}


@router.post("/integrations/rotate")
async def rotate_keys(request: Request, ctx: TenantCtx = Depends(require_role("admin")),
                      db: AsyncSession = Depends(get_db)):
    old = await _active_key(db, ctx.id)
    old.revoked_at = utcnow()
    new, secret, whsec = await issue_api_key(db, ctx.id, list(old.allowed_origins or []))
    await audit(db, request, "keys.rotate", tenant_id=ctx.id, actor=ctx.user, target=new.public_key)
    return {"key": _key(new), "secret_key": secret, "webhook_secret": whsec,
            "warning": "Secret key faqat hozir ko'rsatiladi. Uni xavfsiz joyga saqlang."}


class OriginsIn(BaseModel):
    allowed_origins: list[str] = Field(max_length=50)


@router.put("/integrations/origins")
async def set_origins(body: OriginsIn, request: Request, ctx: TenantCtx = Depends(require_role("admin")),
                      db: AsyncSession = Depends(get_db)):
    key = await _active_key(db, ctx.id)
    clean = sorted({o.strip().lower().rstrip("/") for o in body.allowed_origins if o.strip()})
    key.allowed_origins = clean
    flag_modified(key, "allowed_origins")
    await audit(db, request, "keys.origins", tenant_id=ctx.id, actor=ctx.user, meta={"origins": clean})
    return _key(key)


class PlatformIn(BaseModel):
    platform: Literal["woocommerce", "shopify", "opencart", "laravel", "custom", "nextjs", "html"]


@router.put("/integrations/platform")
async def set_platform(body: PlatformIn, ctx: TenantCtx = Depends(require_role("admin"))):
    ctx.tenant.platform = body.platform
    adapter = body.platform if body.platform in ("woocommerce", "shopify", "opencart") else "none"
    ctx.tenant.settings = {**(ctx.tenant.settings or {}), "cart_adapter": adapter}
    flag_modified(ctx.tenant, "settings")
    return {"ok": True, "cart_adapter": adapter}


@router.get("/integrations/install-check")
async def install_check(ctx: TenantCtx = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    """Integratsiya diagnostikasi: xatolarni ertaroq ushlash."""
    key = await _active_key(db, ctx.id)
    last_widget_event = (await db.execute(tq(Event, ctx.id, func.max(Event.ts)).where(Event.source == "widget"))).scalar_one()
    last_search = (await db.execute(tq(VisualSearch, ctx.id, func.max(VisualSearch.created_at)))).scalar_one()
    last_server = (await db.execute(tq(Event, ctx.id, func.max(Event.ts)).where(Event.source.in_(("webhook", "server"))))).scalar_one()
    last_sync = (await db.execute(tq(CatalogSyncRun, ctx.id).order_by(CatalogSyncRun.id.desc()).limit(1))).scalar_one_or_none()
    failed_webhooks = (await db.execute(tq(WebhookDelivery, ctx.id, func.count()).where(
        WebhookDelivery.status == "failed", WebhookDelivery.created_at >= utcnow() - timedelta(days=7)))).scalar_one()
    now = utcnow()
    widget_seen = max([t for t in (last_widget_event, last_search) if t], default=None)

    def status(ok: bool, warn: bool = False) -> str:
        return "ok" if ok else ("warn" if warn else "error")

    checks = [
        {"key": "widget", "title": "Vidjet saytda o'rnatilgan",
         "status": status(bool(widget_seen) and now - widget_seen < timedelta(hours=24), bool(widget_seen)),
         "detail": f"Oxirgi signal: {widget_seen:%Y-%m-%d %H:%M} UTC" if widget_seen else "Vidjetdan hali signal kelmagan"},
        {"key": "origins", "title": "Domen allowlist sozlangan",
         "status": status(bool(key.allowed_origins), True),
         "detail": ", ".join(key.allowed_origins) if key.allowed_origins else
         "Allowlist bo'sh — kalit istalgan domendan ishlaydi. Domeningizni qo'shing."},
        {"key": "events", "title": "Hodisalar kelmoqda (24 soat)",
         "status": status(bool(last_widget_event) and now - last_widget_event < timedelta(hours=24), bool(last_widget_event)),
         "detail": f"Oxirgi hodisa: {last_widget_event:%Y-%m-%d %H:%M} UTC" if last_widget_event else "Hodisa yo'q"},
        {"key": "webhook", "title": "Buyurtma webhook'i ishlayapti",
         "status": status(bool(last_server) and failed_webhooks == 0, not last_server),
         "detail": (f"Oxirgi buyurtma: {last_server:%Y-%m-%d %H:%M} UTC" if last_server else "Webhook orqali buyurtma kelmagan")
         + (f" · 7 kunda {failed_webhooks} ta xato" if failed_webhooks else "")},
        {"key": "catalog", "title": "Katalog sinxroni",
         "status": status(bool(last_sync) and last_sync.status == "success", not last_sync),
         "detail": (f"{last_sync.status} · {last_sync.items_seen} ta mahsulot · {last_sync.error or ''}"
                    if last_sync else "Hali sinxron qilinmagan")},
    ]
    return {"checks": checks, "score": sum(c["status"] == "ok" for c in checks), "total": len(checks)}


@router.post("/integrations/test-event")
async def test_event(ctx: TenantCtx = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    """Ulanishni tekshirish: test hodisa yuboradi va webhook imzosi namunasini qaytaradi."""
    key = await _active_key(db, ctx.id)
    ev = EventIn(event_id=uuid.uuid4(), type="RESULT_VIEW", session_id=f"test_{secrets.token_hex(6)}")
    r = await ingest(db, ctx.tenant, ev, source="server")
    ts = str(int(time.time()))
    body = json.dumps({"order_ref": "TEST-1", "items": [{"id": "1", "qty": 1, "price_minor": 100}], "currency": "UZS"})
    sig = sign_payload(decrypt(key.webhook_secret_enc), ts, body.encode())
    return {"event_accepted": r["accepted"] == 1,
            "signature_example": {"X-Timestamp": ts, "X-Signature": sig, "body": body}}


# ======================= Jamoa =======================
@router.get("/members")
async def members(ctx: TenantCtx = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(TenantMembership.role, TenantMembership.created_at, User)
                             .join(User, User.id == TenantMembership.user_id)
                             .where(TenantMembership.tenant_id == ctx.id).order_by(TenantMembership.created_at))).all()
    return {"items": [{"user_id": u.id, "email": u.email, "full_name": u.full_name, "role": role,
                       "last_login_at": u.last_login_at, "joined_at": joined, "is_me": u.id == ctx.user.id}
                      for role, joined, u in rows]}


Role = Literal["owner", "admin", "catalog_manager", "analyst", "viewer"]


class InviteIn(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=200)
    role: Role


def _assert_can_assign(ctx: TenantCtx, role: str) -> None:
    if role == "owner" and ctx.role != "owner":
        raise Forbidden("Faqat owner boshqa owner tayinlay oladi")
    if ROLE_RANK[role] > ROLE_RANK[ctx.role]:
        raise Forbidden("O'zingizdan yuqori rol bera olmaysiz")


@router.post("/members")
async def invite(body: InviteIn, request: Request, ctx: TenantCtx = Depends(require_role("admin")),
                 db: AsyncSession = Depends(get_db)):
    _assert_can_assign(ctx, body.role)
    email = body.email.lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    temp_password = None
    if not user:
        temp_password = secrets.token_urlsafe(9) + "7a"
        user = User(email=email, full_name=body.full_name, password_hash=hash_password(temp_password))
        db.add(user)
        await db.flush()
    if await db.get(TenantMembership, (user.id, ctx.id)):
        raise AppError("ALREADY_MEMBER", "Bu foydalanuvchi allaqachon a'zo", 409)
    db.add(TenantMembership(user_id=user.id, tenant_id=ctx.id, role=body.role))
    await audit(db, request, "members.invite", tenant_id=ctx.id, actor=ctx.user, target=user.id, meta={"role": body.role})
    return {"ok": True, "temp_password": temp_password,
            "message": "Vaqtinchalik parol faqat bir marta ko'rsatiladi" if temp_password else "Mavjud foydalanuvchi qo'shildi"}


class RoleIn(BaseModel):
    role: Role


async def _owners(db: AsyncSession, tenant_id: str) -> int:
    return (await db.execute(select(func.count()).select_from(TenantMembership).where(
        TenantMembership.tenant_id == tenant_id, TenantMembership.role == "owner"))).scalar_one()


@router.put("/members/{user_id}")
async def change_role(user_id: str, body: RoleIn, request: Request, ctx: TenantCtx = Depends(require_role("admin")),
                      db: AsyncSession = Depends(get_db)):
    m = await db.get(TenantMembership, (user_id, ctx.id))
    if not m:
        raise NotFound("A'zo topilmadi")
    _assert_can_assign(ctx, body.role)
    if m.role == "owner" and ctx.role != "owner":
        raise Forbidden("Owner rolini faqat owner o'zgartira oladi")
    if m.role == "owner" and body.role != "owner" and await _owners(db, ctx.id) <= 1:
        raise AppError("LAST_OWNER", "Do'konda kamida bitta owner qolishi kerak", 409)
    m.role = body.role
    await audit(db, request, "members.role", tenant_id=ctx.id, actor=ctx.user, target=user_id, meta={"role": body.role})
    return {"ok": True}


@router.delete("/members/{user_id}")
async def remove_member(user_id: str, request: Request, ctx: TenantCtx = Depends(require_role("admin")),
                        db: AsyncSession = Depends(get_db)):
    m = await db.get(TenantMembership, (user_id, ctx.id))
    if not m:
        raise NotFound("A'zo topilmadi")
    if m.role == "owner" and (ctx.role != "owner" or await _owners(db, ctx.id) <= 1):
        raise AppError("LAST_OWNER", "Oxirgi owner'ni o'chirib bo'lmaydi", 409)
    await db.delete(m)
    await audit(db, request, "members.remove", tenant_id=ctx.id, actor=ctx.user, target=user_id)
    return {"ok": True}


# ======================= Sozlamalar =======================
class SettingsIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    unmet_threshold: float | None = Field(default=None, ge=0.1, le=0.95)
    language: Literal["uz", "ru", "en"] | None = None
    theme: dict[str, Any] | None = None
    search_selector: str | None = Field(default=None, max_length=300)
    consent_mode: Literal["implied", "explicit"] | None = None
    attribution_days: int | None = Field(default=None, ge=1, le=30)
    abandon_after_hours: int | None = Field(default=None, ge=1, le=168)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, max_length=64)
    customer_deeplink: str | None = Field(default=None, max_length=500)
    thank_you_url_pattern: str | None = Field(default=None, max_length=300)


@router.get("/settings")
async def get_settings(ctx: TenantCtx = Depends(require_role("viewer"))):
    t = ctx.tenant
    return {"id": t.id, "name": t.name, "slug": t.slug, "plan": t.plan, "status": t.status,
            "catalog_mode": t.catalog_mode, "platform": t.platform, "role": ctx.role,
            "settings": {**DEFAULT_TENANT_SETTINGS, **(t.settings or {})}}


@router.patch("/settings")
async def update_settings(body: SettingsIn, request: Request, ctx: TenantCtx = Depends(require_role("admin")),
                          db: AsyncSession = Depends(get_db)):
    data = body.model_dump(exclude_none=True)
    if name := data.pop("name", None):
        ctx.tenant.name = name
    if "timezone" in data:
        from zoneinfo import ZoneInfo
        try:
            ZoneInfo(data["timezone"])
        except Exception:
            raise AppError("INVALID_TIMEZONE", "Vaqt zonasi noto'g'ri (masalan Asia/Tashkent)", 422)
    if "currency" in data:
        data["currency"] = data["currency"].upper()
    if "theme" in data:
        primary = str(data["theme"].get("primary", "#6d28d9"))[:9]
        position = data["theme"].get("position", "bottom-right")
        data["theme"] = {"primary": primary, "position": position if position in ("bottom-right", "bottom-left") else "bottom-right"}
    ctx.tenant.settings = {**(ctx.tenant.settings or {}), **data}
    flag_modified(ctx.tenant, "settings")
    await audit(db, request, "settings.update", tenant_id=ctx.id, actor=ctx.user, meta={"keys": list(data)})
    return await get_settings(ctx)

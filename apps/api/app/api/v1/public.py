"""Vidjet uchun ochiq API (public key + Origin)."""
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_db, public_tenant
from app.core.cache import cache_get, cache_set, hit_rate_limit
from app.core.config import settings
from app.core.errors import AppError
from app.db.repositories import tq
from typing import Literal

from fastapi import Query

from app.models import Campaign, CatalogProduct, Tenant
from app.services.marketing.recommend import personal_recommendations
from app.services.media import abs_url
from app.services import search as search_service
from app.services.events.collector import EventIn, ingest, touch_session
from app.services.events.identity import link_identity

router = APIRouter(prefix="/v1/public", tags=["public (vidjet)"])

MAX_UPLOAD = 12 * 1024 * 1024  # brauzerda kichraytiriladi; server baribir MAX_IMAGE_MB bilan tekshiradi


@router.get("/config/{public_key}")
async def widget_config(public_key: str, request: Request, db: AsyncSession = Depends(get_db)):
    cache_key = f"cfg:{public_key}"
    if cached := await cache_get(cache_key):
        return cached
    tenant = await public_tenant(request, x_vision_key=public_key, db=db)
    s = tenant.settings or {}
    cfg = {
        "tenant": tenant.slug,
        "plan": tenant.plan,
        "language": s.get("language", "uz"),
        "theme": s.get("theme", {}),
        "search_selector": s.get("search_selector", ""),
        "cart_adapter": s.get("cart_adapter", "none"),
        "consent_mode": s.get("consent_mode", "implied"),
        "attribution_days": s.get("attribution_days", 7),
        "thank_you_url_pattern": s.get("thank_you_url_pattern", ""),
        "currency": s.get("currency", "UZS"),
        "api_url": settings.PUBLIC_API_URL,
    }
    await cache_set(cache_key, cfg, 300)
    return cfg


@router.post("/visual-search")
async def visual_search(
    request: Request,
    background: BackgroundTasks,
    image: UploadFile = File(...),
    session_id: str | None = Form(default=None, max_length=64),
    customer_ref: str | None = Form(default=None, max_length=128),
    consent: bool = Form(default=True),
    hint: str = Form(default="", max_length=200),
    device: str | None = Form(default=None, max_length=16),
    tenant: Tenant = Depends(public_tenant),
):
    raw = await image.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD:
        raise AppError("IMAGE_TOO_LARGE", f"Rasm hajmi {settings.MAX_IMAGE_MB}MB dan oshmasligi kerak", 413)
    hint = f"{hint} {image.filename or ''}".strip()
    result = await search_service.visual_search(
        tenant, raw, session_id=session_id, customer_ref=customer_ref, consent=consent,
        hint=hint, ip=client_ip(request), device=device)
    background.add_task(search_service.persist_search, tenant.id, result["record"], result["session"])
    return result["response"]


class EventsBatch(BaseModel):
    events: list[EventIn] = Field(min_length=1, max_length=50)
    consent: bool | None = None


@router.post("/events")
async def events(request: Request, tenant: Tenant = Depends(public_tenant), db: AsyncSession = Depends(get_db)):
    """navigator.sendBeacon text/plain yuboradi (preflight'siz), shuning uchun body qo'lda o'qiladi."""
    if await hit_rate_limit(f"ev:{client_ip(request)}", 300):
        raise AppError("RATE_LIMITED", "Juda ko'p hodisa", 429)
    raw = await request.body()
    if len(raw) > 256 * 1024:
        raise AppError("PAYLOAD_TOO_LARGE", "Hodisalar paketi juda katta", 413)
    try:
        batch = EventsBatch.model_validate_json(raw)
    except ValidationError as exc:
        raise AppError("VALIDATION_ERROR", "Hodisa formati noto'g'ri",
                       422, {"fields": [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()[:10]]})
    accepted = duplicates = 0
    sessions = {e.session_id for e in batch.events if e.session_id}
    for sid in sessions:
        await touch_session(db, tenant.id, sid, batch.consent)
    for ev in batch.events:
        if ev.type == "PURCHASE" and not ev.order_ref:
            continue  # brauzerdan xarid faqat order_ref bilan (webhook bilan birlashtirish uchun)
        if batch.consent is False:
            ev.customer_ref = None
        r = await ingest(db, tenant, ev, source="widget")
        accepted += r["accepted"]
        duplicates += r["duplicates"]
    return {"accepted": accepted, "duplicates": duplicates}


class IdentifyIn(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    customer_ref: str = Field(min_length=1, max_length=128)
    consent: bool = False


@router.post("/identify")
async def identify(body: IdentifyIn, tenant: Tenant = Depends(public_tenant), db: AsyncSession = Depends(get_db)):
    if not body.consent:
        return {"linked": False, "reason": "consent=false — L0 (anonim) rejimda qoladi"}
    await touch_session(db, tenant.id, body.session_id, True)
    await link_identity(db, tenant.id, body.session_id, body.customer_ref)
    return {"linked": True}


@router.get("/products")
async def products(q: str = "", category: str | None = None, limit: int = 12,
                   tenant: Tenant = Depends(public_tenant), db: AsyncSession = Depends(get_db)):
    stmt = tq(CatalogProduct, tenant.id).where(CatalogProduct.is_deleted.is_(False))
    if category:
        stmt = stmt.where(CatalogProduct.category == category)
    if q:
        like = f"%{q[:60]}%"
        stmt = stmt.where(or_(CatalogProduct.name.like(like), CatalogProduct.description.like(like)))
    rows = (await db.execute(stmt.order_by(CatalogProduct.popularity.desc()).limit(min(limit, 50)))).scalars().all()
    return {"products": [{
        "id": p.external_id, "name": p.name, "price_minor": p.price_minor, "currency": p.currency,
        "image_url": abs_url(p.image_url), "product_url": p.product_url, "in_stock": p.in_stock, "category": p.category,
        "compare_at_minor": p.compare_at_minor,
    } for p in rows]}


@router.get("/recommendations")
async def recommendations(session_id: str | None = None, limit: int = Query(8, ge=1, le=24),
                          tenant: Tenant = Depends(public_tenant), db: AsyncSession = Depends(get_db)):
    """Saytdagi shaxsiy blok: shu sessiya/xaridor qiziqishiga mos mahsulotlar + mos kampaniya banneri.
    Shaxs aniqlanmaydi: faqat vd_sid va (bo'lsa) identify qilingan customer_ref profili ishlatiladi."""
    return await personal_recommendations(db, tenant, session_id, limit)


class CampaignEventIn(BaseModel):
    campaign_id: str = Field(min_length=8, max_length=36)
    kind: Literal["impression", "click"]


@router.post("/campaign-event")
async def campaign_event(body: CampaignEventIn, tenant: Tenant = Depends(public_tenant), db: AsyncSession = Depends(get_db)):
    c = (await db.execute(tq(Campaign, tenant.id).where(Campaign.id == body.campaign_id))).scalar_one_or_none()
    if c:
        stats = dict(c.stats or {})
        key = "impressions" if body.kind == "impression" else "clicks"
        stats[key] = int(stats.get(key, 0)) + 1
        c.stats = stats
    return {"ok": True}

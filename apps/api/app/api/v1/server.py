"""Sotuvchi serveri uchun API (secret key / HMAC). Brauzerdan chaqirilmaydi."""
import json

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, server_tenant
from app.core.errors import AppError
from app.core.security import decrypt, verify_signature
from app.db.base import utcnow
from app.models import ApiKey, Tenant, WebhookDelivery
from app.services.catalog.sync import upsert_products
from app.services.events.collector import EventIn, ingest
from app.services.events.identity import delete_customer, validate_customer_ref
from app.services.webhooks import handlers

router = APIRouter(prefix="/v1/server", tags=["server (secret key)"])


def _check_hmac(key: ApiKey, ts: str | None, sig: str | None, body: bytes, required: bool) -> None:
    if not sig and not required:
        return
    if not verify_signature(decrypt(key.webhook_secret_enc), ts, body, sig):
        raise AppError("INVALID_SIGNATURE", "HMAC imzo yoki X-Timestamp noto'g'ri (±5 daq)", 401)


@router.post("/events")
async def server_events(request: Request, auth=Depends(server_tenant), db: AsyncSession = Depends(get_db),
                        x_timestamp: str | None = Header(default=None), x_signature: str | None = Header(default=None)):
    tenant, key = auth
    body = await request.body()
    _check_hmac(key, x_timestamp, x_signature, body, required=False)
    try:
        payload = json.loads(body or b"{}")
        events = [EventIn.model_validate(e) for e in (payload["events"] if "events" in payload else [payload])]
    except (ValueError, KeyError, TypeError, ValidationError) as exc:
        raise AppError("VALIDATION_ERROR", f"Hodisa formati noto'g'ri: {str(exc)[:300]}", 422)
    accepted = duplicates = 0
    for ev in events[:200]:
        r = await ingest(db, tenant, ev, source="server")
        accepted += r["accepted"]
        duplicates += r["duplicates"]
    return {"accepted": accepted, "duplicates": duplicates}


@router.post("/webhooks/{platform}")
async def webhook(platform: str, request: Request, key: str, db: AsyncSession = Depends(get_db),
                  x_timestamp: str | None = Header(default=None), x_signature: str | None = Header(default=None)):
    """URL: /v1/server/webhooks/{platform}?key=pk_live_...  Imzo: HMAC-SHA256(ts + '.' + body)."""
    api_key = (await db.execute(select(ApiKey).where(ApiKey.public_key == key, ApiKey.revoked_at.is_(None)))).scalar_one_or_none()
    if not api_key:
        raise AppError("INVALID_KEY", "Kalit noto'g'ri", 401)
    tenant = await db.get(Tenant, api_key.tenant_id)
    body = await request.body()
    _check_hmac(api_key, x_timestamp, x_signature, body, required=True)

    try:
        payload = json.loads(body)
    except ValueError:
        raise AppError("INVALID_JSON", "JSON noto'g'ri", 400)
    order_id, ev = handlers.parse(platform, payload)

    # Takror webhook'dan himoya: UNIQUE(tenant, source, external_id)
    res = await db.execute(insert(WebhookDelivery).prefix_with("IGNORE").values(
        tenant_id=tenant.id, source=platform, external_id=order_id, payload=payload, status="received",
        attempts=1, created_at=utcnow()))
    if res.rowcount == 0:
        return {"status": "duplicate", "order_ref": order_id}

    delivery = (await db.execute(select(WebhookDelivery).where(
        WebhookDelivery.tenant_id == tenant.id, WebhookDelivery.source == platform,
        WebhookDelivery.external_id == order_id))).scalar_one()
    try:
        r = await ingest(db, tenant, ev, source="webhook")
        delivery.status = "processed"
    except AppError as exc:
        delivery.status, delivery.error = "failed", exc.message
        raise
    return {"status": "processed", "order_ref": order_id, **r}


class CatalogPush(BaseModel):
    products: list[dict] = Field(min_length=1, max_length=5000)
    full_snapshot: bool = False


@router.post("/catalog/push")
async def catalog_push(body: CatalogPush, auth=Depends(server_tenant), db: AsyncSession = Depends(get_db)):
    tenant, _ = auth
    run = await upsert_products(db, tenant.id, body.products, full_snapshot=body.full_snapshot, source="push")
    return {"status": run.status, "items_seen": run.items_seen, "items_changed": run.items_changed,
            "items_deleted": run.items_deleted, "error": run.error}


@router.delete("/customers/{customer_ref}")
async def forget_customer(customer_ref: str, auth=Depends(server_tenant), db: AsyncSession = Depends(get_db)):
    tenant, _ = auth
    counts = await delete_customer(db, tenant.id, validate_customer_ref(customer_ref))
    return {"status": "anonymized", "affected": counts}


# ---------- Target marketing: sotuvchi serveri auditoriyani o'zi oladi ----------
@router.get("/profiles/{customer_ref}")
async def customer_profile(customer_ref: str, auth=Depends(server_tenant), db: AsyncSession = Depends(get_db)):
    """Bitta xaridorning qiziqishlari + tavsiya mahsulotlar (sotuvchi e-mail/SMS shablonini shu bilan to'ldiradi)."""
    from app.db.repositories import tq
    from app.models import CatalogProduct, CustomerProfile
    from app.services.marketing.profiles import recommend_from_interests, segment_label
    from app.services.media import abs_url

    tenant, _ = auth
    p = (await db.execute(tq(CustomerProfile, tenant.id).where(
        CustomerProfile.profile_key == validate_customer_ref(customer_ref)))).scalar_one_or_none()
    if not p:
        raise AppError("NOT_FOUND", "Profil topilmadi (hali faollik yo'q yoki identify qilinmagan)", 404)
    products = (await db.execute(tq(CatalogProduct, tenant.id).where(CatalogProduct.is_deleted.is_(False)))).scalars().all()
    return {"customer_ref": p.customer_ref, "interests": p.interests,
            "segments": [{"key": s, "label": segment_label(s)} for s in p.segments or []],
            "stats": {"searches": p.searches, "clicks": p.clicks, "carts": p.carts, "purchases": p.purchases,
                      "revenue_minor": p.revenue_minor, "abandoned_minor": p.abandoned_minor, "last_seen": p.last_seen},
            "recommended": [{"id": r.external_id, "name": r.name, "price_minor": r.price_minor,
                             "image_url": abs_url(r.image_url), "url": r.product_url}
                            for r in recommend_from_interests(p.interests, products, limit=6)]}


@router.get("/audiences")
async def audience(segment: str = "all", limit: int = 1000, auth=Depends(server_tenant), db: AsyncSession = Depends(get_db)):
    """Segmentdagi customer_ref'lar + qiziqish + tavsiyalar. Kontaktni sotuvchi o'z bazasidan topadi."""
    from app.models import Campaign
    from app.services.marketing.campaigns import recipients

    tenant, _ = auth
    c = Campaign(id="api-pull", tenant_id=tenant.id, name="api", segment=segment, channel="export")
    return {"segment": segment, "recipients": await recipients(db, tenant, c, limit=min(limit, 5000))}

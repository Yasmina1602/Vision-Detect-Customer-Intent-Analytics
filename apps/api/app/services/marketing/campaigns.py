"""Kampaniyalar: segment → qabul qiluvchilar (customer_ref + qiziqish + tavsiyalar) → sotuvchi webhook'i.

Biz e-mail/SMS yubormaymiz (kontaktni bilmaymiz). Sotuvchi serveri payload'ni qabul qilib, customer_ref bo'yicha
o'z bazasidan kontaktni topadi va o'z kanali (e-mail, SMS, Telegram bot, push) orqali yuboradi.
Imzo: X-Signature = HMAC-SHA256(webhook_secret, X-Timestamp + "." + body).
"""
import json
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt, sign_payload
from app.db.base import utcnow
from app.db.repositories import tq
from app.models import ApiKey, Campaign, CatalogProduct, CustomerProfile, Tenant
from app.services.marketing.profiles import recommend_from_interests
from app.services.media import abs_url

BATCH = 500


def segment_filter(stmt, segment: str):
    """JSON massivda segment bor-yo'qligi (MySQL JSON_CONTAINS)."""
    if segment == "all":
        return stmt
    return stmt.where(func.json_contains(CustomerProfile.segments, json.dumps(segment)))


def with_campaign(url: str, campaign_id: str) -> str:
    parts = urlparse(url)
    q = [(k, v) for k, v in parse_qsl(parts.query) if k != "vd_c"] + [("vd_c", campaign_id[:8])]
    return urlunparse(parts._replace(query=urlencode(q)))


async def audience_count(db: AsyncSession, tenant_id: str, segment: str, identified_only: bool = True) -> int:
    stmt = segment_filter(tq(CustomerProfile, tenant_id, func.count()), segment)
    if identified_only:
        stmt = stmt.where(CustomerProfile.customer_ref.is_not(None))
    return (await db.execute(stmt)).scalar_one()


async def recipients(db: AsyncSession, tenant: Tenant, campaign: Campaign, identified_only: bool = True,
                     limit: int | None = None) -> list[dict[str, Any]]:
    stmt = segment_filter(tq(CustomerProfile, tenant.id), campaign.segment)
    if identified_only:
        stmt = stmt.where(CustomerProfile.customer_ref.is_not(None))
    stmt = stmt.order_by(CustomerProfile.last_seen.desc())
    if limit:
        stmt = stmt.limit(limit)
    profiles = (await db.execute(stmt)).scalars().all()
    products = (await db.execute(tq(CatalogProduct, tenant.id).where(
        CatalogProduct.is_deleted.is_(False), CatalogProduct.in_stock.is_(True)))).scalars().all()
    out = []
    for p in profiles:
        recs = recommend_from_interests(p.interests, products, limit=4)
        out.append({
            "customer_ref": p.customer_ref,
            "top_interests": {d: list((p.interests or {}).get(d, {}).keys())[:3] for d in ("category", "type", "color")},
            "segments": p.segments,
            "abandoned_cart_minor": p.abandoned_minor,
            "products": [{"id": r.external_id, "name": r.name, "price_minor": r.price_minor, "currency": r.currency,
                          "image_url": abs_url(r.image_url), "url": with_campaign(r.product_url, campaign.id)} for r in recs],
        })
    return out


async def send_campaign(db: AsyncSession, tenant: Tenant, campaign: Campaign) -> dict[str, Any]:
    url = tenant.setting("marketing_webhook_url")
    recs = await recipients(db, tenant, campaign)
    campaign.audience_size = len(recs)
    stats = dict(campaign.stats or {})
    if campaign.channel == "onsite":
        campaign.status = "active"
        campaign.sent_at = utcnow()
        return {"status": "active", "recipients": len(recs)}
    if campaign.channel != "webhook":
        campaign.status = "sent"
        campaign.sent_at = utcnow()
        return {"status": "exported", "recipients": len(recs)}
    if not url:
        stats["error"] = "Sozlamalarda 'Marketing webhook URL' kiritilmagan"
        campaign.stats = stats
        return {"status": "error", "error": stats["error"]}

    key = (await db.execute(tq(ApiKey, tenant.id).where(ApiKey.revoked_at.is_(None)).limit(1))).scalar_one()
    secret = decrypt(key.webhook_secret_enc)
    sent = 0
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=10) as client:
        for i in range(0, max(len(recs), 1), BATCH):
            chunk = recs[i:i + BATCH]
            if not chunk:
                break
            body = json.dumps({
                "type": "campaign.send", "campaign": {"id": campaign.id, "name": campaign.name, "title": campaign.title,
                                                      "message": campaign.message, "discount_code": campaign.discount_code,
                                                      "segment": campaign.segment},
                "recipients": chunk,
            }, ensure_ascii=False, default=str).encode()
            ts = str(int(time.time()))
            try:
                r = await client.post(url, content=body, headers={
                    "Content-Type": "application/json", "X-Timestamp": ts,
                    "X-Signature": sign_payload(secret, ts, body), "X-Vision-Event": "campaign.send"})
                if r.status_code < 300:
                    sent += len(chunk)
                else:
                    errors.append(f"HTTP {r.status_code}")
            except httpx.HTTPError as exc:
                errors.append(str(exc)[:200])
    stats.update({"sent": sent, "error": "; ".join(errors) or None})
    campaign.stats = stats
    campaign.status = "sent" if sent else campaign.status
    campaign.sent_at = utcnow() if sent else campaign.sent_at
    return {"status": "sent" if sent else "error", "recipients": len(recs), "sent": sent, "error": stats["error"]}

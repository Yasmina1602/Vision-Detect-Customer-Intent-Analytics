"""Saytdagi shaxsiy tavsiyalar (on-site targeting). Profil bo'lmasa — sessiyaning oxirgi qidiruvlaridan tezkor hisob."""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import tq
from app.models import Campaign, CatalogProduct, CustomerProfile, IdentityLink, Tenant, VisualSearch
from app.services.marketing.profiles import recommend_from_interests
from app.services.media import abs_url


async def personal_recommendations(db: AsyncSession, tenant: Tenant, session_id: str | None, limit: int = 8) -> dict[str, Any]:
    profile = None
    if session_id:
        ref = (await db.execute(select(IdentityLink.customer_ref).where(
            IdentityLink.tenant_id == tenant.id, IdentityLink.session_id == session_id).limit(1))).scalar_one_or_none()
        for key in filter(None, [ref, f"s:{session_id}"]):
            profile = (await db.execute(tq(CustomerProfile, tenant.id).where(CustomerProfile.profile_key == key))).scalar_one_or_none()
            if profile:
                break

    interests: dict[str, dict[str, float]] = dict(profile.interests or {}) if profile else {}
    if not interests and session_id:   # yangi tashrif — profil hali qurilmagan
        interests = {"category": {}, "color": {}, "type": {}}
        for s in (await db.execute(tq(VisualSearch, tenant.id).where(VisualSearch.session_id == session_id)
                                   .order_by(VisualSearch.created_at.desc()).limit(20))).scalars().all():
            ai = s.ai_detected or {}
            for dim in ("category", "color", "type"):
                v = ai.get(dim)
                if v and v != "boshqa":
                    interests[dim][v] = interests[dim].get(v, 0) + 1

    products = (await db.execute(tq(CatalogProduct, tenant.id).where(
        CatalogProduct.is_deleted.is_(False), CatalogProduct.in_stock.is_(True)))).scalars().all()
    recs = recommend_from_interests(interests, products, limit=limit)
    personalized = bool(recs)
    if not recs:    # qiziqish noma'lum — eng mashhurlar
        recs = sorted(products, key=lambda p: -((p.sales_count or 0) + (p.popularity or 0) * 10))[:limit]

    banner = None
    segs = set(profile.segments or []) if profile else set()
    campaigns = (await db.execute(tq(Campaign, tenant.id).where(Campaign.channel == "onsite", Campaign.status == "active")
                                  .order_by(Campaign.created_at.desc()))).scalars().all()
    for c in campaigns:
        if c.segment == "all" or c.segment in segs:
            banner = {"campaign_id": c.id, "title": c.title, "message": c.message, "discount_code": c.discount_code}
            break

    return {
        "personalized": personalized,
        "interests": {d: list(v.keys())[:3] for d, v in interests.items()} if interests else {},
        "banner": banner,
        "products": [{"id": p.external_id, "name": p.name, "price_minor": p.price_minor, "compare_at_minor": p.compare_at_minor,
                      "currency": p.currency, "image_url": abs_url(p.image_url), "product_url": p.product_url}
                     for p in recs],
    }



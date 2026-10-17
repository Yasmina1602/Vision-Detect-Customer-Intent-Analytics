"""Xaridor qiziqishlari profili (PII'siz) va segmentlar.

Har bir profil — customer_ref (identify qilingan xaridor) yoki "s:<vd_sid>" (anonim sessiya).
Qiziqish og'irliklari: qidiruv 1, bosish 2, savat 3, xarid 4; 30 kunlik yarim yemirilish (eski qiziqish so'nadi).

Target reklama qanday ishlaydi (biz shaxsni bilmaymiz):
  1) Sotuvchi webhook'i — kampaniya customer_ref + qiziqishlar + tavsiya mahsulotlar ro'yxatini sotuvchi serveriga
     yuboradi; sotuvchi o'z bazasida customer_ref → e-mail/telefon/Telegram'ni topib, xabarni O'ZI jo'natadi.
  2) Saytdagi shaxsiy blok — vidjet anonim sessiyaga ham uning qiziqishiga mos mahsulot/banner ko'rsatadi.
  3) Eksport (CSV/Excel) — customer_ref ro'yxati sotuvchining CRM/reklama kabinetiga yuklanadi.
  4) Premium (do'kon bizda): marketing_consent=true mijozlar uchun kontakt bilan eksport.
"""
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.repositories import tq
from app.models import CartSession, CatalogProduct, CustomerProfile, Event, IdentityLink, Tenant, VisualSearch

WEIGHTS = {"SEARCH": 1.0, "PRODUCT_CLICK": 2.0, "ADD_TO_CART": 3.0, "PURCHASE": 4.0}
HALF_LIFE_DAYS = 30
WINDOW_DAYS = 90

SEGMENT_LABELS = {
    "abandoned_cart": "Savatni tashlab ketganlar",
    "buyer": "Xaridorlar",
    "repeat_buyer": "Takroriy xaridorlar",
    "high_value": "Katta xarid qiluvchilar",
    "browser": "Ko'rib ketganlar (xaridsiz)",
    "unmet_demand": "Topa olmaganlar (qondirilmagan talab)",
    "identified": "Tanilgan xaridorlar (customer_ref)",
}


def segment_label(key: str) -> str:
    if key in SEGMENT_LABELS:
        return SEGMENT_LABELS[key]
    kind, _, value = key.partition(":")
    return {"interest": f"Qiziqish: {value}", "color": f"Rang: {value}", "type": f"Tur: {value}",
            "unmet": f"Topilmagan: {value.replace('|', ' ').replace('-', '').strip()}"}.get(kind, key)


def _decay(ts: datetime, now: datetime) -> float:
    age = max(0.0, (now - ts).total_seconds() / 86400)
    return math.pow(0.5, age / HALF_LIFE_DAYS)


def _add(bucket: dict[str, float], key: str | None, w: float) -> None:
    if key and key not in ("boshqa", "-", "null", "None"):
        bucket[key] = bucket.get(key, 0.0) + w


async def rebuild_profiles(db: AsyncSession, tenant: Tenant) -> int:
    """Oxirgi 90 kunlik hodisalardan profillarni qayta hisoblaydi (idempotent)."""
    now = utcnow()
    since = now - timedelta(days=WINDOW_DAYS)
    tid = tenant.id

    links = {sid: ref for sid, ref in (await db.execute(
        select(IdentityLink.session_id, IdentityLink.customer_ref).where(IdentityLink.tenant_id == tid))).all()}

    def key_for(session_id: str | None, customer_ref: str | None) -> str | None:
        ref = customer_ref or (links.get(session_id) if session_id else None)
        if ref:
            return ref
        return f"s:{session_id}" if session_id else None

    prof: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "category": {}, "color": {}, "type": {}, "unmet": set(), "searches": 0, "clicks": 0, "carts": 0,
        "purchases": set(), "revenue": 0, "abandoned": 0, "last_seen": None, "session": None, "ref": None})

    def touch(p: dict, ts: datetime, session_id: str | None, ref: str | None) -> None:
        p["last_seen"] = max(p["last_seen"] or ts, ts)
        p["session"] = p["session"] or session_id
        p["ref"] = p["ref"] or ref or (links.get(session_id) if session_id else None)

    for s in (await db.execute(tq(VisualSearch, tid).where(VisualSearch.created_at >= since))).scalars().all():
        k = key_for(s.session_id, s.customer_ref)
        if not k:
            continue
        p = prof[k]
        w = WEIGHTS["SEARCH"] * _decay(s.created_at, now)
        ai = s.ai_detected or {}
        _add(p["category"], ai.get("category"), w)
        _add(p["color"], ai.get("color"), w)
        _add(p["type"], ai.get("type"), w)
        p["searches"] += 1
        if s.is_unmet_demand and s.demand_key:
            p["unmet"].add(s.demand_key)
        touch(p, s.created_at, s.session_id, s.customer_ref)

    products = {p.external_id: p for p in (await db.execute(
        tq(CatalogProduct, tid).where(CatalogProduct.is_deleted.is_(False)))).scalars().all()}

    for e in (await db.execute(tq(Event, tid).where(
            Event.ts >= since, Event.type.in_(("PRODUCT_CLICK", "ADD_TO_CART", "PURCHASE"))))).scalars().all():
        k = key_for(e.session_id, e.customer_ref)
        if not k:
            continue
        p = prof[k]
        w = WEIGHTS[e.type] * _decay(e.ts, now)
        prod = products.get(e.product_external_id or "")
        if prod:
            _add(p["category"], prod.category, w)
            _add(p["color"], prod.color, w)
            _add(p["type"], (prod.attributes or {}).get("type"), w)
        if e.type == "PRODUCT_CLICK":
            p["clicks"] += 1
        elif e.type == "ADD_TO_CART":
            p["carts"] += 1
        elif e.type == "PURCHASE":
            p["purchases"].add(e.order_ref or e.event_id)
            p["revenue"] += (e.price_minor or 0) * (e.qty or 1)
        touch(p, e.ts, e.session_id, e.customer_ref)

    for c in (await db.execute(tq(CartSession, tid).where(
            CartSession.state == "abandoned", CartSession.last_activity_at >= since))).scalars().all():
        k = key_for(c.session_id, c.customer_ref)
        if k:
            prof[k]["abandoned"] += c.total_minor or 0
            touch(prof[k], c.last_activity_at, c.session_id, c.customer_ref)

    high_value = sorted((p["revenue"] for p in prof.values() if p["revenue"]), reverse=True)
    hv_threshold = high_value[max(0, len(high_value) // 5 - 1)] if len(high_value) >= 5 else float("inf")

    count = 0
    for k, p in prof.items():
        interests = {dim: dict(sorted(((n, round(v, 3)) for n, v in p[dim].items()), key=lambda x: -x[1])[:8])
                     for dim in ("category", "color", "type")}
        segs: list[str] = []
        for dim, prefix in (("category", "interest"), ("color", "color"), ("type", "type")):
            if interests[dim]:
                segs.append(f"{prefix}:{next(iter(interests[dim]))}")
        n_purch = len(p["purchases"])
        if p["abandoned"]:
            segs.append("abandoned_cart")
        if n_purch:
            segs.append("buyer")
        if n_purch >= 2:
            segs.append("repeat_buyer")
        if p["revenue"] and p["revenue"] >= hv_threshold:
            segs.append("high_value")
        if not n_purch and (p["clicks"] or p["searches"] >= 2):
            segs.append("browser")
        if p["unmet"]:
            segs.append("unmet_demand")
            segs.extend(f"unmet:{u}" for u in sorted(p["unmet"])[:5])
        if p["ref"]:
            segs.append("identified")

        values = dict(customer_ref=p["ref"], session_id=p["session"], interests=interests, segments=segs,
                      unmet=sorted(p["unmet"])[:20], searches=p["searches"], clicks=p["clicks"], carts=p["carts"],
                      purchases=n_purch, revenue_minor=p["revenue"], abandoned_minor=p["abandoned"],
                      last_seen=p["last_seen"], updated_at=now)
        await db.execute(insert(CustomerProfile).values(tenant_id=tid, profile_key=k[:140], **values)
                         .on_duplicate_key_update(**values))
        count += 1
    return count


def recommend_from_interests(interests: dict, products: list[CatalogProduct], exclude: set[str] | None = None,
                             limit: int = 8) -> list[CatalogProduct]:
    """Qiziqishlarga mos, zaxirada bor mahsulotlar (kategoriya 3, tur 4, rang 2 og'irlik bilan)."""
    exclude = exclude or set()
    cat, col, typ = (interests or {}).get("category", {}), (interests or {}).get("color", {}), (interests or {}).get("type", {})
    scored = []
    for p in products:
        if not p.in_stock or p.external_id in exclude:
            continue
        s = 3 * cat.get(p.category or "", 0) + 4 * typ.get((p.attributes or {}).get("type") or "", 0) + 2 * col.get(p.color or "", 0)
        if s > 0:
            scored.append((s + (p.popularity or 0) * 0.1, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:limit]]

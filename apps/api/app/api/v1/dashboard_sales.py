"""Dashboard: savdo (buyurtmalar, mijozlar — Premium), auditoriya va kampaniyalar, rasm yuklash."""
import csv
import io
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import TenantCtx, audit, get_db, require_premium, require_role
from app.core.errors import AppError, NotFound
from app.core.security import short_hash
from app.db.repositories import tq
from app.models import Campaign, CatalogProduct, Customer, CustomerProfile, Event, IdentityLink, Order
from app.services import storefront as sf
from app.services.analytics.common import local_date_expr, make_range
from app.services.marketing import campaigns as camp
from app.services.marketing.profiles import SEGMENT_LABELS, rebuild_profiles, recommend_from_interests, segment_label
from app.services.media import abs_url, save_product_image
from app.services.vision import router as vision_router
from app.services.vision.image_utils import sanitize_image

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard: savdo va marketing"])


# ======================= Rasm yuklash =======================
@router.post("/catalog/images")
async def upload_image(file: UploadFile = File(...), analyze: bool = False,
                       ctx: TenantCtx = Depends(require_role("catalog_manager")), db: AsyncSession = Depends(get_db)):
    raw = await file.read(8 * 1024 * 1024 + 1)
    path = save_product_image(ctx.id, raw)
    out: dict = {"path": path, "url": abs_url(path)}
    if analyze:   # AI bilan kategoriya/rang/turni avtomatik to'ldirish
        try:
            jpeg, _ = sanitize_image(raw)
            ai, model = await vision_router.analyze(db, jpeg, file.filename or "")
            out["ai"] = ai.model_dump()
        except AppError as exc:
            out["ai_error"] = exc.message
    return out


# ======================= Buyurtmalar (Premium) =======================
@router.get("/orders")
async def orders(status: str | None = None, q: str = "", page: int = Query(1, ge=1), size: int = Query(20, le=100),
                 date_from: date | None = Query(None, alias="from"), date_to: date | None = Query(None, alias="to"),
                 ctx: TenantCtx = Depends(require_role("analyst")), db: AsyncSession = Depends(get_db)):
    require_premium(ctx)
    r = make_range(ctx.tenant, date_from, date_to)
    base = tq(Order, ctx.id).where(Order.created_at >= r.start_utc, Order.created_at < r.end_utc)
    if q:
        like = f"%{q}%"
        base = base.where(or_(Order.number.like(like), Order.customer_name.like(like), Order.phone.like(like)))
    counts = dict((await db.execute(base.with_only_columns(Order.status, func.count()).group_by(Order.status))).all())
    stmt = base.where(Order.status == status) if status else base
    total = (await db.execute(stmt.with_only_columns(func.count()))).scalar_one()
    rows = (await db.execute(stmt.order_by(Order.created_at.desc()).offset((page - 1) * size).limit(size))).scalars().all()

    valid = base.where(Order.status != "cancelled")
    revenue, n_orders = (await db.execute(valid.with_only_columns(func.coalesce(func.sum(Order.total_minor), 0), func.count()))).one()
    paid = (await db.execute(valid.where(Order.payment_status == "paid").with_only_columns(
        func.coalesce(func.sum(Order.total_minor), 0)))).scalar_one()
    day = local_date_expr(Order.created_at, r.offset_min)
    series = {d.isoformat(): {"orders": 0, "revenue_minor": 0} for d in r.local_days()}
    for d, n, s in (await db.execute(valid.with_only_columns(day, func.count(), func.sum(Order.total_minor)).group_by(day))).all():
        if str(d) in series:
            series[str(d)] = {"orders": int(n), "revenue_minor": int(s or 0)}
    return {
        "summary": {"revenue_minor": int(revenue), "paid_minor": int(paid), "orders": int(n_orders),
                    "avg_order_minor": int(revenue / n_orders) if n_orders else 0, "currency": ctx.tenant.setting("currency"),
                    "by_status": counts},
        "series": [{"date": k, **v} for k, v in series.items()],
        "total": total, "page": page, "size": size,
        "items": [{"id": o.id, "number": o.number, "status": o.status, "status_label": sf.STATUS_LABELS.get(o.status),
                   "payment_status": o.payment_status, "payment_method": o.payment_method,
                   "delivery_method": o.delivery_method, "customer_name": o.customer_name, "phone": o.phone,
                   "total_minor": o.total_minor, "currency": o.currency, "created_at": o.created_at,
                   "from_search": bool(o.search_id)} for o in rows],
    }


@router.get("/orders/{order_id}")
async def order_detail(order_id: str, ctx: TenantCtx = Depends(require_role("analyst")), db: AsyncSession = Depends(get_db)):
    require_premium(ctx)
    o = (await db.execute(tq(Order, ctx.id).where(Order.id == order_id))).scalar_one_or_none()
    if not o:
        raise NotFound("Buyurtma topilmadi")
    return await sf.order_view(db, o)


class StatusIn(BaseModel):
    status: Literal["new", "confirmed", "shipped", "delivered", "cancelled"]


@router.patch("/orders/{order_id}")
async def order_status(order_id: str, body: StatusIn, request: Request,
                       ctx: TenantCtx = Depends(require_role("catalog_manager")), db: AsyncSession = Depends(get_db)):
    require_premium(ctx)
    o = (await db.execute(tq(Order, ctx.id).where(Order.id == order_id).with_for_update())).scalar_one_or_none()
    if not o:
        raise NotFound("Buyurtma topilmadi")
    await sf.change_status(db, ctx.tenant, o, body.status)
    await audit(db, request, "orders.status", tenant_id=ctx.id, actor=ctx.user, target=o.number, meta={"status": body.status})
    return await sf.order_view(db, o)


@router.get("/customers")
async def customers(q: str = "", ref: str | None = None, page: int = Query(1, ge=1), size: int = Query(25, le=100),
                    ctx: TenantCtx = Depends(require_role("analyst")), db: AsyncSession = Depends(get_db)):
    """Tanilgan xaridorlar ro'yxati (customer_ref). Ikkala tarifda ishlaydi.

    Oddiy tarif: faqat neytral customer_ref + faollik (kontakt sotuvchining o'z tizimida).
    Premium: do'kon o'zimizda — ism/telefon/e-mail va buyurtmalar ham qo'shiladi.
    """
    rows: dict[str, dict] = {}

    def row(r: str) -> dict:
        return rows.setdefault(r, {
            "customer_ref": r, "full_name": None, "email": None, "phone": None, "city": None, "marketing_consent": None,
            "registered_at": None, "first_seen": None, "last_seen": None, "sessions": 0, "searches": 0, "carts": 0,
            "purchases": 0, "revenue_minor": 0, "abandoned_minor": 0, "orders": 0, "spent_minor": 0,
            "last_order_at": None, "interests": [], "segments": []})

    for r, first, last, n in (await db.execute(
            select(IdentityLink.customer_ref, func.min(IdentityLink.linked_at), func.max(IdentityLink.linked_at), func.count())
            .where(IdentityLink.tenant_id == ctx.id).group_by(IdentityLink.customer_ref))).all():
        x = row(r)
        x.update(first_seen=first, last_seen=last, sessions=int(n))
    for (r,) in (await db.execute(tq(Event, ctx.id, Event.customer_ref).where(Event.customer_ref.is_not(None)).distinct())).all():
        row(r)
    for p in (await db.execute(tq(CustomerProfile, ctx.id).where(CustomerProfile.customer_ref.is_not(None)))).scalars().all():
        x = row(p.customer_ref)
        x.update(searches=p.searches, carts=p.carts, purchases=p.purchases, revenue_minor=p.revenue_minor,
                 abandoned_minor=p.abandoned_minor,
                 interests=[v for d in ("type", "category", "color") for v in list((p.interests or {}).get(d, {}))[:1]],
                 segments=[segment_label(s) for s in (p.segments or []) if s in SEGMENT_LABELS and s != "identified"])
        if p.last_seen and (not x["last_seen"] or p.last_seen > x["last_seen"]):
            x["last_seen"] = p.last_seen

    premium = ctx.tenant.plan == "premium"
    if premium:
        custs = (await db.execute(tq(Customer, ctx.id))).scalars().all()
        stats = {cid: (n, s, last) for cid, n, s, last in (await db.execute(
            tq(Order, ctx.id, Order.customer_id, func.count(), func.sum(Order.total_minor), func.max(Order.created_at))
            .where(Order.customer_id.is_not(None), Order.status != "cancelled").group_by(Order.customer_id))).all()}
        for c in custs:
            x = row(c.customer_ref)
            n, s, last = stats.get(c.id, (0, 0, None))
            x.update(full_name=c.full_name, email=c.email, phone=c.phone, city=c.city, marketing_consent=c.marketing_consent,
                     registered_at=c.created_at, orders=int(n), spent_minor=int(s or 0), last_order_at=last)
            x["last_seen"] = max(filter(None, [x["last_seen"], last, c.created_at]), default=None)

    items = list(rows.values())
    if ref:
        items = [i for i in items if i["customer_ref"] == ref]
    elif q:
        ql = q.lower()
        items = [i for i in items if ql in " ".join(str(i[k] or "") for k in ("customer_ref", "full_name", "email", "phone")).lower()]
    items.sort(key=lambda i: i["last_seen"] or i["registered_at"] or datetime.min, reverse=True)
    total = len(items)
    return {"total": total, "page": page, "size": size, "premium": premium,
            "items": items[(page - 1) * size: page * size]}


# ======================= Auditoriya =======================
@router.post("/audiences/rebuild")
async def rebuild(ctx: TenantCtx = Depends(require_role("analyst")), db: AsyncSession = Depends(get_db)):
    n = await rebuild_profiles(db, ctx.tenant)
    return {"profiles": n}


@router.get("/audiences")
async def audiences(ctx: TenantCtx = Depends(require_role("analyst")), db: AsyncSession = Depends(get_db)):
    profiles = (await db.execute(tq(CustomerProfile, ctx.id))).scalars().all()
    counts: dict[str, dict] = {}
    for p in profiles:
        for s in p.segments or []:
            c = counts.setdefault(s, {"key": s, "label": segment_label(s), "size": 0, "identified": 0, "abandoned_minor": 0})
            c["size"] += 1
            c["identified"] += 1 if p.customer_ref else 0
            c["abandoned_minor"] += p.abandoned_minor or 0
    order = list(SEGMENT_LABELS)
    segs = sorted(counts.values(), key=lambda s: (s["key"].split(":")[0] not in order and 1 or 0, -s["size"]))
    last = max((p.updated_at for p in profiles), default=None)
    return {"total_profiles": len(profiles), "identified": sum(1 for p in profiles if p.customer_ref),
            "updated_at": last, "segments": segs,
            "webhook_configured": bool(ctx.tenant.setting("marketing_webhook_url"))}


@router.get("/audiences/profiles")
async def audience_profiles(segment: str = "all", q: str = "", page: int = Query(1, ge=1), size: int = Query(25, le=100),
                            ctx: TenantCtx = Depends(require_role("analyst")), db: AsyncSession = Depends(get_db)):
    stmt = camp.segment_filter(tq(CustomerProfile, ctx.id), segment)
    if q:
        stmt = stmt.where(CustomerProfile.customer_ref.like(f"%{q}%"))
    total = (await db.execute(stmt.with_only_columns(func.count()))).scalar_one()
    rows = (await db.execute(stmt.order_by(CustomerProfile.last_seen.desc()).offset((page - 1) * size).limit(size))).scalars().all()
    products = (await db.execute(tq(CatalogProduct, ctx.id).where(CatalogProduct.is_deleted.is_(False)))).scalars().all()
    deeplink = ctx.tenant.setting("customer_deeplink") or ""
    return {"total": total, "page": page, "size": size, "items": [{
        "key": p.profile_key,
        "label": f"Mijoz #{short_hash(p.customer_ref)}" if p.customer_ref else f"Anonim #{short_hash(p.profile_key)}",
        "customer_ref": p.customer_ref,
        "customer_link": deeplink.replace("{customer_ref}", p.customer_ref) if deeplink and p.customer_ref else None,
        "interests": {d: list((p.interests or {}).get(d, {}).keys())[:3] for d in ("category", "type", "color")},
        "segments": [{"key": s, "label": segment_label(s)} for s in (p.segments or []) if not s.startswith(("interest:", "color:", "type:"))],
        "searches": p.searches, "clicks": p.clicks, "carts": p.carts, "purchases": p.purchases,
        "revenue_minor": p.revenue_minor, "abandoned_minor": p.abandoned_minor, "last_seen": p.last_seen,
        "recommended": [{"id": r.external_id, "name": r.name, "image_url": abs_url(r.image_url)}
                        for r in recommend_from_interests(p.interests, products, limit=3)],
    } for p in rows]}


@router.get("/audiences/export")
async def audience_export(segment: str = "all", request: Request = None,  # type: ignore[assignment]
                          ctx: TenantCtx = Depends(require_role("analyst")), db: AsyncSession = Depends(get_db)):
    """CSV: customer_ref + qiziqishlar + tavsiya mahsulotlar. Premium'da marketing roziligi bergan mijozlar kontakti bilan."""
    c = Campaign(id="export", tenant_id=ctx.id, name="export", segment=segment, channel="export")
    recs = await camp.recipients(db, ctx.tenant, c, identified_only=True)
    contacts: dict[str, Customer] = {}
    if ctx.tenant.plan == "premium":
        for cust in (await db.execute(tq(Customer, ctx.id).where(Customer.marketing_consent.is_(True)))).scalars().all():
            contacts[cust.customer_ref] = cust
    await audit(db, request, "audiences.export", tenant_id=ctx.id, actor=ctx.user, target=segment, meta={"rows": len(recs)})
    buf = io.StringIO()
    buf.write("﻿")
    w = csv.writer(buf)
    w.writerow(["customer_ref", "qiziqish_kategoriya", "qiziqish_tur", "qiziqish_rang", "segmentlar",
                "tashlangan_savat", "tavsiya_1", "tavsiya_2", "tavsiya_3", "ism", "telefon", "email"])
    for r in recs:
        cust = contacts.get(r["customer_ref"])
        prods = [f"{p['name']} {p['url']}" for p in r["products"][:3]] + [""] * 3
        w.writerow([r["customer_ref"], ", ".join(r["top_interests"]["category"]), ", ".join(r["top_interests"]["type"]),
                    ", ".join(r["top_interests"]["color"]), ", ".join(r["segments"]), r["abandoned_cart_minor"] / 100,
                    *prods[:3], cust.full_name if cust else "", cust.phone if cust else "", cust.email if cust else ""])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="auditoriya_{segment.replace(":", "-")}.csv"'})


# ======================= Kampaniyalar =======================
def _campaign(c: Campaign) -> dict:
    return {"id": c.id, "name": c.name, "segment": c.segment, "segment_label": segment_label(c.segment),
            "channel": c.channel, "title": c.title, "message": c.message, "discount_code": c.discount_code,
            "status": c.status, "audience_size": c.audience_size, "stats": c.stats or {}, "sent_at": c.sent_at,
            "created_at": c.created_at}


@router.get("/campaigns")
async def campaigns(ctx: TenantCtx = Depends(require_role("analyst")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(tq(Campaign, ctx.id).order_by(Campaign.created_at.desc()))).scalars().all()
    return {"items": [_campaign(c) for c in rows], "webhook_url": ctx.tenant.setting("marketing_webhook_url") or ""}


class CampaignIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    segment: str = Field(min_length=2, max_length=191)
    channel: Literal["webhook", "onsite", "export"] = "onsite"
    title: str = Field(min_length=2, max_length=200)
    message: str = Field(default="", max_length=2000)
    discount_code: str | None = Field(default=None, max_length=50)


@router.post("/campaigns")
async def create_campaign(body: CampaignIn, request: Request, ctx: TenantCtx = Depends(require_role("admin")),
                          db: AsyncSession = Depends(get_db)):
    c = Campaign(tenant_id=ctx.id, created_by=ctx.user.id, status="draft", stats={}, **body.model_dump())
    db.add(c)
    await db.flush()
    c.audience_size = await camp.audience_count(db, ctx.id, c.segment, identified_only=body.channel != "onsite")
    await audit(db, request, "campaigns.create", tenant_id=ctx.id, actor=ctx.user, target=c.id)
    return _campaign(c)


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(campaign_id: str, request: Request, ctx: TenantCtx = Depends(require_role("admin")),
                        db: AsyncSession = Depends(get_db)):
    c = (await db.execute(tq(Campaign, ctx.id).where(Campaign.id == campaign_id))).scalar_one_or_none()
    if not c:
        raise NotFound("Kampaniya topilmadi")
    result = await camp.send_campaign(db, ctx.tenant, c)
    flag_modified(c, "stats")
    await audit(db, request, "campaigns.send", tenant_id=ctx.id, actor=ctx.user, target=c.id, meta=result)
    return {"campaign": _campaign(c), "result": result}


@router.post("/campaigns/{campaign_id}/stop")
async def stop_campaign(campaign_id: str, ctx: TenantCtx = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    c = (await db.execute(tq(Campaign, ctx.id).where(Campaign.id == campaign_id))).scalar_one_or_none()
    if not c:
        raise NotFound("Kampaniya topilmadi")
    c.status = "stopped"
    return _campaign(c)


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str, ctx: TenantCtx = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    c = (await db.execute(tq(Campaign, ctx.id).where(Campaign.id == campaign_id))).scalar_one_or_none()
    if not c:
        raise NotFound("Kampaniya topilmadi")
    await db.delete(c)
    return {"ok": True}


class MarketingSettings(BaseModel):
    marketing_webhook_url: HttpUrl | Literal[""] = ""


@router.put("/campaigns-settings")
async def campaign_settings(body: MarketingSettings, ctx: TenantCtx = Depends(require_role("admin"))):
    ctx.tenant.settings = {**(ctx.tenant.settings or {}), "marketing_webhook_url": str(body.marketing_webhook_url)}
    flag_modified(ctx.tenant, "settings")
    return {"ok": True}


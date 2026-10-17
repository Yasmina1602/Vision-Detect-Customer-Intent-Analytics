"""Metrikalar (README 13-bo'lim) — barcha sahifalar bir xil ta'riflardan foydalanadi."""
from collections import defaultdict
from typing import Any

from sqlalchemy import Integer, and_, cast, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import short_hash
from app.db.repositories import tq
from app.models import CartSession, Event, Tenant, UnmetDemandCluster, VisualSearch
from app.services.analytics.common import DateRange, delta_pct, local_date_expr, pct

AI_CAT = func.json_unquote(func.json_extract(VisualSearch.ai_detected, "$.category"))
AI_COLOR = func.json_unquote(func.json_extract(VisualSearch.ai_detected, "$.color"))
AI_TYPE = func.json_unquote(func.json_extract(VisualSearch.ai_detected, "$.type"))
AI_QUERY = func.json_unquote(func.json_extract(VisualSearch.ai_detected, "$.search_query"))


def bsum(col):
    """SUM(boolean) — natija Boolean emas, butun son bo'lishi uchun cast."""
    return func.coalesce(func.sum(cast(col, Integer)), 0)


def _in_range(col, r: DateRange):
    return and_(col >= r.start_utc, col < r.end_utc)


async def _search_ids_with(db: AsyncSession, tenant_id: str, r: DateRange, event_type: str) -> int:
    """Hodisa bog'langan noyob qidiruvlar (qidiruv shu oraliqda bo'lgan)."""
    stmt = (select(func.count(distinct(Event.search_id)))
            .select_from(Event)
            .join(VisualSearch, and_(VisualSearch.id == Event.search_id, VisualSearch.tenant_id == Event.tenant_id))
            .where(Event.tenant_id == tenant_id, Event.type == event_type, _in_range(VisualSearch.created_at, r)))
    return (await db.execute(stmt)).scalar_one() or 0


async def _kpis(db: AsyncSession, tenant: Tenant, r: DateRange) -> dict[str, Any]:
    tid = tenant.id
    row = (await db.execute(
        tq(VisualSearch, tid, func.count(), func.count(distinct(VisualSearch.session_id)),
           bsum(VisualSearch.from_cache),
           bsum(VisualSearch.is_unmet_demand),
           func.avg(VisualSearch.latency_ms))
        .where(_in_range(VisualSearch.created_at, r))
    )).one()
    searches, searchers, cached, unmet, avg_latency = row
    carted = await _search_ids_with(db, tid, r, "ADD_TO_CART")
    purchased = await _search_ids_with(db, tid, r, "PURCHASE")

    lost = (await db.execute(
        tq(CartSession, tid, CartSession.currency, func.sum(CartSession.total_minor), func.count())
        .where(CartSession.state == "abandoned", _in_range(CartSession.closed_at, r))
        .group_by(CartSession.currency)
    )).all()
    revenue = (await db.execute(
        tq(Event, tid, Event.currency, func.sum(Event.price_minor * Event.qty))
        .where(Event.type == "PURCHASE", Event.search_id.is_not(None), _in_range(Event.ts, r))
        .group_by(Event.currency)
    )).all()
    return {
        "searches": int(searches or 0),
        "searchers": int(searchers or 0),
        "from_cache": int(cached or 0),
        "unmet_demand": int(unmet or 0),
        "avg_latency_ms": int(avg_latency or 0),
        "add_to_cart": carted,
        "purchases": purchased,
        "conversion_pct": pct(purchased, searches or 0),
        "cart_rate_pct": pct(carted, searches or 0),
        "lost_revenue": [{"currency": c or tenant.setting("currency"), "amount_minor": int(s or 0), "carts": n}
                         for c, s, n in lost],
        "attributed_revenue": [{"currency": c or tenant.setting("currency"), "amount_minor": int(s or 0)}
                               for c, s in revenue],
    }


def _money_total(items: list[dict[str, Any]], currency: str) -> int:
    return sum(i["amount_minor"] for i in items if i["currency"] == currency)


async def overview(db: AsyncSession, tenant: Tenant, r: DateRange) -> dict[str, Any]:
    cur = await _kpis(db, tenant, r)
    prev = await _kpis(db, tenant, r.previous())
    currency = tenant.setting("currency")
    deltas = {k: delta_pct(cur[k], prev[k]) for k in ("searches", "searchers", "add_to_cart", "purchases",
                                                       "conversion_pct", "unmet_demand")}
    deltas["lost_revenue"] = delta_pct(_money_total(cur["lost_revenue"], currency),
                                       _money_total(prev["lost_revenue"], currency))
    deltas["attributed_revenue"] = delta_pct(_money_total(cur["attributed_revenue"], currency),
                                             _money_total(prev["attributed_revenue"], currency))

    # Kunlik dinamika
    day = local_date_expr(VisualSearch.created_at, r.offset_min)
    s_rows = (await db.execute(
        tq(VisualSearch, tenant.id, day, func.count(), bsum(VisualSearch.is_unmet_demand))
        .where(_in_range(VisualSearch.created_at, r)).group_by(day)
    )).all()
    eday = local_date_expr(Event.ts, r.offset_min)
    e_rows = (await db.execute(
        tq(Event, tenant.id, eday, Event.type, func.count(distinct(Event.search_id)))
        .where(_in_range(Event.ts, r), Event.type.in_(("ADD_TO_CART", "PURCHASE")), Event.search_id.is_not(None))
        .group_by(eday, Event.type)
    )).all()
    series: dict[str, dict[str, int]] = {d.isoformat(): {"searches": 0, "unmet": 0, "add_to_cart": 0, "purchases": 0}
                                         for d in r.local_days()}
    for d, n, unmet in s_rows:
        if (k := str(d)) in series:
            series[k]["searches"], series[k]["unmet"] = int(n), int(unmet)
    for d, typ, n in e_rows:
        if (k := str(d)) in series:
            series[k]["add_to_cart" if typ == "ADD_TO_CART" else "purchases"] = int(n)

    return {
        "range": {"from": r.start_local.isoformat(), "to": r.end_local.isoformat()},
        "currency": currency,
        "kpis": cur,
        "previous": prev,
        "deltas": deltas,
        "series": [{"date": k, **v} for k, v in series.items()],
    }


async def funnel(db: AsyncSession, tenant: Tenant, r: DateRange) -> dict[str, Any]:
    tid = tenant.id
    searched = (await db.execute(tq(VisualSearch, tid, func.count()).where(_in_range(VisualSearch.created_at, r)))).scalar_one()
    with_results = (await db.execute(tq(VisualSearch, tid, func.count())
                                     .where(_in_range(VisualSearch.created_at, r), VisualSearch.results_count > 0))).scalar_one()
    viewed_ev = await _search_ids_with(db, tid, r, "RESULT_VIEW")
    viewed = max(viewed_ev, 0) or with_results
    clicked = await _search_ids_with(db, tid, r, "PRODUCT_CLICK")
    carted = await _search_ids_with(db, tid, r, "ADD_TO_CART")
    purchased = await _search_ids_with(db, tid, r, "PURCHASE")

    steps = [("searched", "Qidirdi", searched), ("viewed", "Natija ko'rdi", viewed), ("clicked", "Mahsulot bosdi", clicked),
             ("carted", "Savatga soldi", carted), ("purchased", "Xarid qildi", purchased)]
    out = []
    prev_n = None
    for key, label, n in steps:
        out.append({"key": key, "label": label, "count": int(n), "pct_of_total": pct(n, searched),
                    "pct_of_prev": pct(n, prev_n) if prev_n is not None else 100.0,
                    "drop": int(prev_n - n) if prev_n is not None else 0})
        prev_n = n
    return {"steps": out, "no_results": int(searched - with_results)}


async def demand(db: AsyncSession, tenant: Tenant, r: DateRange, limit: int = 100) -> dict[str, Any]:
    tid = tenant.id
    rows = (await db.execute(
        tq(VisualSearch, tid, VisualSearch.demand_key, func.count(), func.count(distinct(VisualSearch.session_id)),
           func.min(VisualSearch.created_at), func.max(VisualSearch.created_at), func.max(AI_QUERY),
           func.max(AI_CAT), func.max(AI_COLOR), func.max(AI_TYPE))
        .where(VisualSearch.is_unmet_demand.is_(True), _in_range(VisualSearch.created_at, r))
        .group_by(VisualSearch.demand_key)
        .order_by(func.count().desc()).limit(limit)
    )).all()
    suggestions = {c.demand_key: c.ai_suggestion for c in (await db.execute(
        tq(UnmetDemandCluster, tid))).scalars().all()}
    items = []
    for key, n, sessions, first, last, query, cat, color, typ in rows:
        items.append({
            "demand_key": key, "sample_query": query, "category": cat, "color": color, "type": typ,
            "search_count": int(n), "unique_sessions": int(sessions), "first_seen": first, "last_seen": last,
            "ai_suggestion": suggestions.get(key) or default_suggestion(color, typ, cat, int(n)),
        })
    total = sum(i["search_count"] for i in items)
    return {"items": items, "total_unmet": total}


def default_suggestion(color: str | None, typ: str | None, cat: str | None, n: int) -> str:
    what = " ".join(x for x in [color, typ or cat] if x and x not in ("-", "null")) or "bu mahsulot"
    if n >= 10:
        return f"Yuqori talab: {what} katalogga qo'shilsa, oyiga ~{n} qidiruv sotuvga aylanishi mumkin."
    return f"{what.capitalize()} turini katalogga qo'shishni ko'rib chiqing."


async def abandoned_carts(db: AsyncSession, tenant: Tenant, r: DateRange, limit: int = 100) -> dict[str, Any]:
    tid = tenant.id
    carts = (await db.execute(
        tq(CartSession, tid).where(CartSession.state == "abandoned", _in_range(CartSession.closed_at, r))
        .order_by(CartSession.total_minor.desc())
    )).scalars().all()
    open_count = (await db.execute(tq(CartSession, tid, func.count()).where(CartSession.state == "open"))).scalar_one()
    by_product: dict[str, dict[str, Any]] = defaultdict(lambda: {"qty": 0, "amount_minor": 0, "carts": 0, "name": None})
    for c in carts:
        for it in c.items or []:
            p = by_product[str(it.get("id"))]
            p["qty"] += int(it.get("qty") or 1)
            p["amount_minor"] += int(it.get("price_minor") or 0) * int(it.get("qty") or 1)
            p["carts"] += 1
            p["name"] = p["name"] or it.get("name")
    products = sorted(({"product_id": k, **v} for k, v in by_product.items()), key=lambda x: -x["amount_minor"])
    deeplink = tenant.setting("customer_deeplink") or ""
    return {
        "total_lost_minor": sum(c.total_minor for c in carts),
        "currency": tenant.setting("currency"),
        "abandoned_count": len(carts),
        "open_count": int(open_count),
        "products": products[:limit],
        "carts": [{
            "id": c.id, "customer": f"Mijoz #{short_hash(c.customer_ref)}" if c.customer_ref else "Anonim",
            "customer_link": deeplink.replace("{customer_ref}", c.customer_ref) if deeplink and c.customer_ref else None,
            "items": c.items, "total_minor": c.total_minor, "currency": c.currency,
            "last_activity_at": c.last_activity_at, "from_search": bool(c.search_id),
        } for c in carts[:limit]],
    }


async def searches_log(db: AsyncSession, tenant: Tenant, r: DateRange, page: int, size: int,
                       only_unmet: bool = False) -> dict[str, Any]:
    stmt = tq(VisualSearch, tenant.id).where(_in_range(VisualSearch.created_at, r))
    if only_unmet:
        stmt = stmt.where(VisualSearch.is_unmet_demand.is_(True))
    total = (await db.execute(stmt.with_only_columns(func.count()))).scalar_one()
    rows = (await db.execute(stmt.order_by(VisualSearch.created_at.desc()).offset((page - 1) * size).limit(size))).scalars().all()
    return {
        "total": int(total), "page": page, "size": size,
        "items": [{
            "id": s.id, "created_at": s.created_at, "category": s.ai_detected.get("category"),
            "color": s.ai_detected.get("color"), "type": s.ai_detected.get("type"),
            "query": s.ai_detected.get("search_query"), "confidence": s.ai_detected.get("confidence"),
            "best_score": s.best_score, "results": s.results_count, "unmet": s.is_unmet_demand,
            "model": s.model_used, "from_cache": s.from_cache, "latency_ms": s.latency_ms,
            "customer": f"Mijoz #{short_hash(s.customer_ref)}" if s.customer_ref else None,
        } for s in rows],
    }


async def colors_categories(db: AsyncSession, tenant: Tenant, r: DateRange) -> dict[str, Any]:
    tid = tenant.id
    where = _in_range(VisualSearch.created_at, r)

    async def group(expr, n=12):
        rows = (await db.execute(tq(VisualSearch, tid, expr, func.count(),
                                    bsum(VisualSearch.is_unmet_demand))
                                 .where(where).group_by(expr).order_by(func.count().desc()).limit(n))).all()
        return [{"name": k or "noma'lum", "count": int(c), "unmet": int(u)} for k, c, u in rows]

    hour_rows = (await db.execute(tq(VisualSearch, tid, func.hour(VisualSearch.created_at), func.count())
                                  .where(where).group_by(func.hour(VisualSearch.created_at)))).all()
    hours = [0] * 24
    shift = r.offset_min // 60
    for h, c in hour_rows:
        hours[(int(h) + shift) % 24] += int(c)
    return {
        "colors": await group(AI_COLOR),
        "categories": await group(AI_CAT),
        "types": await group(AI_TYPE, 15),
        "hourly": [{"hour": h, "count": c} for h, c in enumerate(hours)],
    }

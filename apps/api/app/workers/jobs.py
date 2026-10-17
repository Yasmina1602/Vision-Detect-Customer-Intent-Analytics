"""Fon vazifalari. Hammasi idempotent — qayta ishga tushirilsa natija buzilmaydi."""
import logging
from datetime import timedelta

from sqlalchemy import delete, distinct, func, select
from sqlalchemy.dialects.mysql import insert

from app.db.base import utcnow
from app.db.session import SessionLocal
from app.models import (CartSession, DailyStat, Event, ShopperSession, Tenant, UnmetDemandCluster,
                        VisualSearch)
from app.services.analytics.common import make_range
from app.services.analytics.metrics import AI_QUERY, _kpis, default_suggestion, AI_COLOR, AI_TYPE, AI_CAT
from app.services.catalog.sync import sync_tenant_feed

log = logging.getLogger("app.worker")


async def _active_tenants(db) -> list[Tenant]:
    return list((await db.execute(select(Tenant).where(Tenant.status.in_(("active", "trial"))))).scalars().all())


async def detect_abandoned() -> int:
    """open savat abandon_after_hours ichida PURCHASE bo'lmasa → abandoned."""
    total = 0
    async with SessionLocal() as db:
        for t in await _active_tenants(db):
            hours = int(t.setting("abandon_after_hours") or 24)
            cutoff = utcnow() - timedelta(hours=hours)
            carts = (await db.execute(select(CartSession).where(
                CartSession.tenant_id == t.id, CartSession.state == "open",
                CartSession.last_activity_at < cutoff))).scalars().all()
            for c in carts:
                if not c.items:          # hamma narsa olib tashlangan savat — yo'qotish emas
                    await db.delete(c)
                    continue
                c.state = "abandoned"
                c.closed_at = c.last_activity_at + timedelta(hours=hours)
            total += len(carts)
        await db.commit()
    if total:
        log.info("abandoned: %s ta savat belgilandi", total)
    return total


async def aggregate_daily(days: int = 2) -> None:
    """Oxirgi kunlar uchun daily_stats (dashboard tezligi va tarix uchun)."""
    async with SessionLocal() as db:
        for t in await _active_tenants(db):
            r_all = make_range(t, None, None, default_days=days)
            for d in r_all.local_days():
                r = make_range(t, d, d)
                k = await _kpis(db, t, r)
                await db.execute(insert(DailyStat).values(tenant_id=t.id, date=d, metrics=k)
                                 .on_duplicate_key_update(metrics=k))
        await db.commit()


async def cluster_demand() -> None:
    """Qondirilmagan talab klasterlari (demand_key bo'yicha, 90 kun)."""
    since = utcnow() - timedelta(days=90)
    async with SessionLocal() as db:
        for t in await _active_tenants(db):
            rows = (await db.execute(
                select(VisualSearch.demand_key, func.count(), func.count(distinct(VisualSearch.session_id)),
                       func.min(VisualSearch.created_at), func.max(VisualSearch.created_at), func.max(AI_QUERY),
                       func.max(AI_COLOR), func.max(AI_TYPE), func.max(AI_CAT))
                .where(VisualSearch.tenant_id == t.id, VisualSearch.is_unmet_demand.is_(True),
                       VisualSearch.created_at >= since, VisualSearch.demand_key.is_not(None))
                .group_by(VisualSearch.demand_key)
            )).all()
            for key, n, sessions, first, last, query, color, typ, cat in rows:
                values = dict(sample_query=query, search_count=n, unique_sessions=sessions, first_seen=first,
                              last_seen=last, ai_suggestion=default_suggestion(color, typ, cat, n))
                await db.execute(insert(UnmetDemandCluster).values(tenant_id=t.id, demand_key=key, **values)
                                 .on_duplicate_key_update(**values))
        await db.commit()


async def build_profiles() -> None:
    """Auditoriya profillari va segmentlar (target marketing uchun)."""
    from app.services.marketing.profiles import rebuild_profiles
    async with SessionLocal() as db:
        for t in await _active_tenants(db):
            await rebuild_profiles(db, t)
        await db.commit()


async def sync_catalogs() -> None:
    async with SessionLocal() as db:
        for t in await _active_tenants(db):
            if t.catalog_mode == "feed" and t.setting("feed_url"):
                run = await sync_tenant_feed(db, t)
                log.info("feed sync %s: %s (%s)", t.slug, run.status, run.error or "")
                await db.commit()


async def retention() -> None:
    """Xom events/visual_searches 13 oy; harakatsiz sessiyalar 90 kun."""
    async with SessionLocal() as db:
        cutoff = utcnow() - timedelta(days=395)
        await db.execute(delete(Event).where(Event.ts < cutoff))
        await db.execute(delete(VisualSearch).where(VisualSearch.created_at < cutoff))
        await db.execute(delete(ShopperSession).where(ShopperSession.last_seen < utcnow() - timedelta(days=90)))
        await db.commit()

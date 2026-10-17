"""Katalog sinxroni: upsert, o'zgarganini qayta embedding, himoyalar.

- Feed 0 ta mahsulot qaytarsa yoki 50% dan ko'pi yo'qolsa → eski katalog o'chirilmaydi, run=failed.
- O'chirilgan mahsulotlar soft delete (is_deleted=true).
"""
import logging
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.repositories import tq
from app.models import CatalogProduct, CatalogSyncRun, Tenant
from app.services.catalog import providers
from app.services.catalog.normalizer import embedding_text, enrich, from_raw
from app.services.matching.embeddings import embed

log = logging.getLogger("app.catalog.sync")


async def upsert_products(db: AsyncSession, tenant_id: str, rows: list[dict[str, Any]],
                          full_snapshot: bool, source: str) -> CatalogSyncRun:
    run = CatalogSyncRun(tenant_id=tenant_id, source=source, status="running", started_at=utcnow())
    db.add(run)
    await db.flush()

    valid: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for i, raw in enumerate(rows):
        try:
            p = from_raw(raw)
            valid[p.external_id] = enrich(p)
        except ValidationError as exc:
            if len(errors) < 5:
                errors.append(f"#{i + 1}: {exc.errors()[0]['loc'][0]} — {exc.errors()[0]['msg']}")
    run.items_seen = len(rows)

    existing = {p.external_id: p for p in (await db.execute(tq(CatalogProduct, tenant_id))).scalars().all()}
    active_before = sum(1 for p in existing.values() if not p.is_deleted)

    if full_snapshot:
        if not valid:
            run.status, run.error, run.finished_at = "failed", "Feed 0 ta mahsulot qaytardi — katalog saqlab qolindi", utcnow()
            return run
        missing = [eid for eid, p in existing.items() if not p.is_deleted and eid not in valid]
        if active_before >= 10 and len(missing) > active_before * 0.5:
            run.status = "failed"
            run.error = f"{len(missing)}/{active_before} mahsulot yo'qoldi (>50%) — himoya ishladi, katalog o'zgarmadi"
            run.finished_at = utcnow()
            return run

    changed = 0
    for eid, data in valid.items():
        prod = existing.get(eid)
        if prod is None:
            prod = CatalogProduct(tenant_id=tenant_id, **data, embedding=embed(embedding_text(data)))
            db.add(prod)
            changed += 1
        elif prod.content_hash != data["content_hash"] or prod.is_deleted:
            for k, v in data.items():
                setattr(prod, k, v)
            prod.embedding = embed(embedding_text(data))
            prod.is_deleted = False
            changed += 1

    deleted = 0
    if full_snapshot:
        for eid, prod in existing.items():
            if not prod.is_deleted and eid not in valid:
                prod.is_deleted = True
                deleted += 1

    run.items_changed, run.items_deleted = changed, deleted
    run.status = "success"
    invalid = len(rows) - len(valid)
    run.error = f"{invalid} ta qator rad etildi: " + "; ".join(errors) if errors else None
    run.finished_at = utcnow()
    return run


async def sync_tenant_feed(db: AsyncSession, tenant: Tenant) -> CatalogSyncRun:
    url = tenant.setting("feed_url")
    if not url:
        run = CatalogSyncRun(tenant_id=tenant.id, source="feed", status="failed",
                             error="Feed URL sozlanmagan", finished_at=utcnow())
        db.add(run)
        return run
    try:
        rows = await providers.fetch_feed(url, tenant.setting("feed_format"))
    except Exception as exc:
        run = CatalogSyncRun(tenant_id=tenant.id, source="feed", status="failed",
                             error=f"Feed yuklab bo'lmadi: {str(exc)[:300]}", finished_at=utcnow())
        db.add(run)
        return run
    return await upsert_products(db, tenant.id, rows, full_snapshot=True, source="feed")


async def catalog_stats(db: AsyncSession, tenant_id: str) -> dict[str, int]:
    base = tq(CatalogProduct, tenant_id, func.count()).where(CatalogProduct.is_deleted.is_(False))
    total = (await db.execute(base)).scalar_one()
    in_stock = (await db.execute(base.where(CatalogProduct.in_stock.is_(True)))).scalar_one()
    return {"total": total, "in_stock": in_stock, "out_of_stock": total - in_stock}

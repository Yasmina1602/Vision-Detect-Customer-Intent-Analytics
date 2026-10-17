"""Katalog: sinxron holati, mahsulotlar, qo'lda sync, CSV yuklash, Premium CRUD."""
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import TenantCtx, audit, get_db, require_premium, require_role
from app.core.errors import AppError, NotFound
from app.db.repositories import tcount, tget, tq
from app.models import CatalogProduct, CatalogSyncRun
from app.services.catalog import providers
from app.services.catalog.normalizer import ProductIn, embedding_text, enrich
from app.services.catalog.sync import catalog_stats, sync_tenant_feed, upsert_products
from app.services.matching.embeddings import embed
from app.services.media import abs_url

router = APIRouter(prefix="/v1/dashboard/catalog", tags=["dashboard: katalog"])


def _product(p: CatalogProduct) -> dict:
    return {"id": p.id, "external_id": p.external_id, "name": p.name, "description": p.description,
            "category": p.category, "color": p.color, "type": (p.attributes or {}).get("type"),
            "price_minor": p.price_minor, "compare_at_minor": p.compare_at_minor, "currency": p.currency,
            "image_url": abs_url(p.image_url), "image_path": p.image_url, "images": [abs_url(i) for i in (p.images or [])],
            "image_paths": p.images or [],
            "stock_qty": p.stock_qty, "brand": p.brand, "sales_count": p.sales_count,
            "product_url": p.product_url, "in_stock": p.in_stock, "popularity": round(p.popularity or 0, 3),
            "updated_at": p.updated_at}


def _run(r: CatalogSyncRun) -> dict:
    return {"id": r.id, "source": r.source, "status": r.status, "items_seen": r.items_seen,
            "items_changed": r.items_changed, "items_deleted": r.items_deleted, "error": r.error,
            "started_at": r.started_at, "finished_at": r.finished_at}


@router.get("")
async def catalog_summary(ctx: TenantCtx = Depends(require_role("viewer")), db: AsyncSession = Depends(get_db)):
    runs = (await db.execute(tq(CatalogSyncRun, ctx.id).order_by(CatalogSyncRun.id.desc()).limit(10))).scalars().all()
    return {
        "mode": ctx.tenant.catalog_mode, "plan": ctx.tenant.plan,
        "feed_url": ctx.tenant.setting("feed_url"), "feed_format": ctx.tenant.setting("feed_format"),
        "stats": await catalog_stats(db, ctx.id),
        "runs": [_run(r) for r in runs],
        "last_failed": runs[0].status == "failed" if runs else False,
    }


@router.get("/products")
async def list_products(q: str = "", category: str | None = None, in_stock: bool | None = None,
                        page: int = Query(1, ge=1), size: int = Query(24, ge=1, le=100),
                        ctx: TenantCtx = Depends(require_role("viewer")), db: AsyncSession = Depends(get_db)):
    stmt = tq(CatalogProduct, ctx.id).where(CatalogProduct.is_deleted.is_(False))
    cnt = tcount(CatalogProduct, ctx.id).where(CatalogProduct.is_deleted.is_(False))
    if q:
        cond = or_(CatalogProduct.name.like(f"%{q}%"), CatalogProduct.external_id == q)
        stmt, cnt = stmt.where(cond), cnt.where(cond)
    if category:
        stmt, cnt = stmt.where(CatalogProduct.category == category), cnt.where(CatalogProduct.category == category)
    if in_stock is not None:
        stmt, cnt = stmt.where(CatalogProduct.in_stock.is_(in_stock)), cnt.where(CatalogProduct.in_stock.is_(in_stock))
    total = (await db.execute(cnt)).scalar_one()
    rows = (await db.execute(stmt.order_by(CatalogProduct.updated_at.desc()).offset((page - 1) * size).limit(size))).scalars().all()
    return {"total": total, "page": page, "size": size, "items": [_product(p) for p in rows]}


class FeedSettings(BaseModel):
    feed_url: str = Field(default="", max_length=1000)
    feed_format: str = Field(default="json", pattern="^(json|csv|xml)$")


@router.put("/feed")
async def set_feed(body: FeedSettings, request: Request, ctx: TenantCtx = Depends(require_role("catalog_manager")),
                   db: AsyncSession = Depends(get_db)):
    if body.feed_url and not body.feed_url.startswith(("http://", "https://")):
        raise AppError("FEED_URL", "Feed URL http(s):// bilan boshlanishi kerak", 422)
    ctx.tenant.settings = {**(ctx.tenant.settings or {}), "feed_url": body.feed_url, "feed_format": body.feed_format}
    flag_modified(ctx.tenant, "settings")
    await audit(db, request, "catalog.feed_update", tenant_id=ctx.id, actor=ctx.user)
    return {"ok": True}


@router.post("/sync")
async def sync_now(request: Request, ctx: TenantCtx = Depends(require_role("catalog_manager")),
                   db: AsyncSession = Depends(get_db)):
    run = await sync_tenant_feed(db, ctx.tenant)
    await db.flush()
    await audit(db, request, "catalog.sync", tenant_id=ctx.id, actor=ctx.user, meta={"status": run.status})
    return _run(run)


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...), full_snapshot: bool = False,
                      ctx: TenantCtx = Depends(require_role("catalog_manager")), db: AsyncSession = Depends(get_db)):
    raw = await file.read(20 * 1024 * 1024 + 1)
    if len(raw) > 20 * 1024 * 1024:
        raise AppError("FILE_TOO_LARGE", "Fayl 20MB dan oshmasligi kerak", 413)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1251", errors="replace")
    name = (file.filename or "").lower()
    fmt = "json" if name.endswith(".json") else "xml" if name.endswith(".xml") else "csv"
    try:
        rows = providers.parse_feed(text, fmt)
    except Exception as exc:
        raise AppError("FEED_FORMAT", f"Faylni o'qib bo'lmadi: {str(exc)[:200]}", 422)
    run = await upsert_products(db, ctx.id, rows, full_snapshot=full_snapshot, source="csv")
    await db.flush()
    await audit(db, request, "catalog.upload", tenant_id=ctx.id, actor=ctx.user, meta={"rows": len(rows)})
    return _run(run)


# ---------- Premium: qo'lda mahsulot boshqarish (hosted katalog) ----------
@router.post("/products")
async def create_product(body: ProductIn, ctx: TenantCtx = Depends(require_role("catalog_manager")),
                         db: AsyncSession = Depends(get_db)):
    require_premium(ctx)
    if await tget(db, CatalogProduct, ctx.id, external_id=body.external_id):
        raise AppError("DUPLICATE", "Bu ID bilan mahsulot mavjud", 409)
    data = enrich(body)
    p = CatalogProduct(tenant_id=ctx.id, **data, embedding=embed(embedding_text(data)))
    db.add(p)
    await db.flush()
    return _product(p)


@router.get("/products/{product_id}")
async def get_product(product_id: str, ctx: TenantCtx = Depends(require_role("viewer")), db: AsyncSession = Depends(get_db)):
    p = await tget(db, CatalogProduct, ctx.id, id=product_id)
    if not p or p.is_deleted:
        raise NotFound("Mahsulot topilmadi")
    return _product(p)


class StockIn(BaseModel):
    in_stock: bool | None = None
    stock_qty: int | None = Field(default=None, ge=0)


@router.patch("/products/{product_id}")
async def patch_product(product_id: str, body: StockIn, ctx: TenantCtx = Depends(require_role("catalog_manager")),
                        db: AsyncSession = Depends(get_db)):
    """Tezkor o'zgartirish: sotuvda/yo'q va ombor soni (ro'yxatdan turib)."""
    require_premium(ctx)
    p = await tget(db, CatalogProduct, ctx.id, id=product_id)
    if not p:
        raise NotFound("Mahsulot topilmadi")
    if body.stock_qty is not None:
        p.stock_qty = body.stock_qty
        p.in_stock = body.stock_qty > 0
    if body.in_stock is not None:
        p.in_stock = body.in_stock
    return _product(p)


@router.put("/products/{product_id}")
async def update_product(product_id: str, body: ProductIn, ctx: TenantCtx = Depends(require_role("catalog_manager")),
                         db: AsyncSession = Depends(get_db)):
    require_premium(ctx)
    p = await tget(db, CatalogProduct, ctx.id, id=product_id)
    if not p:
        raise NotFound("Mahsulot topilmadi")
    data = enrich(body)
    for k, v in data.items():
        setattr(p, k, v)
    p.embedding = embed(embedding_text(data))
    return _product(p)


@router.delete("/products/{product_id}")
async def delete_product(product_id: str, ctx: TenantCtx = Depends(require_role("catalog_manager")),
                         db: AsyncSession = Depends(get_db)):
    require_premium(ctx)
    p = await tget(db, CatalogProduct, ctx.id, id=product_id)
    if not p:
        raise NotFound("Mahsulot topilmadi")
    p.is_deleted = True   # soft delete
    return {"ok": True}

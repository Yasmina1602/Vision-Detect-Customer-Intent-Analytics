"""Tenant dashboard analitikasi (JWT + rol)."""
import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantCtx, audit, get_db, require_role
from app.core.cache import cache_get, cache_set
from app.services.analytics import metrics
from app.services.analytics.common import make_range
from app.services.export_xlsx import build_workbook

router = APIRouter(prefix="/v1/dashboard/analytics", tags=["dashboard: analitika"])


async def _cached(key: str, coro_fn):
    if (hit := await cache_get(key)) is not None:
        return hit
    value = await coro_fn()
    await cache_set(key, value, 60)
    return value


def _rkey(ctx: TenantCtx, name: str, date_from, date_to, *extra) -> str:
    return f"an:{ctx.id}:{name}:{date_from}:{date_to}:" + ":".join(map(str, extra))


@router.get("/overview")
async def overview(date_from: date | None = Query(None, alias="from"), date_to: date | None = Query(None, alias="to"),
                   ctx: TenantCtx = Depends(require_role("viewer")), db: AsyncSession = Depends(get_db)):
    r = make_range(ctx.tenant, date_from, date_to)
    return await _cached(_rkey(ctx, "overview", r.start_local, r.end_local),
                         lambda: metrics.overview(db, ctx.tenant, r))


@router.get("/funnel")
async def funnel(date_from: date | None = Query(None, alias="from"), date_to: date | None = Query(None, alias="to"),
                 ctx: TenantCtx = Depends(require_role("viewer")), db: AsyncSession = Depends(get_db)):
    r = make_range(ctx.tenant, date_from, date_to)
    return await _cached(_rkey(ctx, "funnel", r.start_local, r.end_local), lambda: metrics.funnel(db, ctx.tenant, r))


@router.get("/demand")
async def demand(date_from: date | None = Query(None, alias="from"), date_to: date | None = Query(None, alias="to"),
                 ctx: TenantCtx = Depends(require_role("analyst")), db: AsyncSession = Depends(get_db)):
    r = make_range(ctx.tenant, date_from, date_to)
    return await _cached(_rkey(ctx, "demand", r.start_local, r.end_local), lambda: metrics.demand(db, ctx.tenant, r))


@router.get("/carts")
async def carts(date_from: date | None = Query(None, alias="from"), date_to: date | None = Query(None, alias="to"),
                ctx: TenantCtx = Depends(require_role("analyst")), db: AsyncSession = Depends(get_db)):
    r = make_range(ctx.tenant, date_from, date_to)
    return await _cached(_rkey(ctx, "carts", r.start_local, r.end_local),
                         lambda: metrics.abandoned_carts(db, ctx.tenant, r))


@router.get("/searches")
async def searches(date_from: date | None = Query(None, alias="from"), date_to: date | None = Query(None, alias="to"),
                   page: int = Query(1, ge=1), size: int = Query(25, ge=5, le=100), unmet: bool = False,
                   ctx: TenantCtx = Depends(require_role("analyst")), db: AsyncSession = Depends(get_db)):
    r = make_range(ctx.tenant, date_from, date_to)
    return await metrics.searches_log(db, ctx.tenant, r, page, size, unmet)


@router.get("/colors")
async def colors(date_from: date | None = Query(None, alias="from"), date_to: date | None = Query(None, alias="to"),
                 ctx: TenantCtx = Depends(require_role("viewer")), db: AsyncSession = Depends(get_db)):
    r = make_range(ctx.tenant, date_from, date_to)
    return await _cached(_rkey(ctx, "colors", r.start_local, r.end_local),
                         lambda: metrics.colors_categories(db, ctx.tenant, r))


@router.get("/export.xlsx")
async def export_xlsx(request: Request, date_from: date | None = Query(None, alias="from"),
                      date_to: date | None = Query(None, alias="to"),
                      ctx: TenantCtx = Depends(require_role("analyst")), db: AsyncSession = Depends(get_db)):
    """Barcha ma'lumotlar bitta Excel faylda (har bo'lim alohida varaqda)."""
    r = make_range(ctx.tenant, date_from, date_to)
    data = await build_workbook(db, ctx.tenant, r)
    await audit(db, request, "analytics.export_xlsx", tenant_id=ctx.id, actor=ctx.user)
    name = f"vision-detect_{ctx.tenant.slug}_{r.start_local}_{r.end_local}.xlsx"
    return StreamingResponse(iter([data]), headers={"Content-Disposition": f'attachment; filename="{name}"'},
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _csv(rows: list[list], header: list[str], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    buf.write("﻿")  # Excel uchun UTF-8 BOM
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/export/{report}")
async def export(report: str, request: Request,
                 date_from: date | None = Query(None, alias="from"), date_to: date | None = Query(None, alias="to"),
                 ctx: TenantCtx = Depends(require_role("analyst")), db: AsyncSession = Depends(get_db)):
    r = make_range(ctx.tenant, date_from, date_to)
    await audit(db, request, "analytics.export", tenant_id=ctx.id, actor=ctx.user, target=report)
    suffix = f"{r.start_local}_{r.end_local}.csv"
    if report == "demand":
        d = await metrics.demand(db, ctx.tenant, r, limit=1000)
        return _csv([[i["demand_key"], i["sample_query"], i["category"], i["color"], i["type"], i["search_count"],
                      i["unique_sessions"], i["ai_suggestion"]] for i in d["items"]],
                    ["demand_key", "sorov", "kategoriya", "rang", "tur", "qidiruvlar", "noyob_sessiyalar", "tavsiya"],
                    f"qondirilmagan-talab_{suffix}")
    if report == "carts":
        d = await metrics.abandoned_carts(db, ctx.tenant, r, limit=5000)
        return _csv([[p["product_id"], p["name"], p["qty"], p["carts"], p["amount_minor"] / 100] for p in d["products"]],
                    ["mahsulot_id", "nomi", "dona", "savatlar", f"summa_{d['currency']}"], f"tashlab-ketilgan_{suffix}")
    if report == "searches":
        d = await metrics.searches_log(db, ctx.tenant, r, 1, 5000)
        return _csv([[s["created_at"], s["category"], s["color"], s["type"], s["query"], s["best_score"], s["results"],
                      s["unmet"], s["from_cache"]] for s in d["items"]],
                    ["vaqt_utc", "kategoriya", "rang", "tur", "sorov", "ball", "natijalar", "qondirilmagan", "kesh"],
                    f"qidiruvlar_{suffix}")
    from app.core.errors import NotFound
    raise NotFound("Hisobot turi topilmadi")

"""Tenant izolyatsiyasi.

MySQL'da PostgreSQL RLS yo'q, shuning uchun har bir tenant jadvaliga so'rov faqat shu yordamchilar
orqali quriladi: tenant_id filtri qo'shilmagan so'rovni yozib bo'lmaydi.
"""
from typing import Any, TypeVar

from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


def _require_tenant(model: Any, tenant_id: str) -> None:
    if not tenant_id:
        raise RuntimeError("tenant_id majburiy (izolyatsiya buzilishi)")
    if not hasattr(model, "tenant_id"):
        raise RuntimeError(f"{model.__name__} tenant jadvali emas")


def tq(model: type[T], tenant_id: str, *columns: Any) -> Select:
    """`SELECT ... FROM model WHERE tenant_id = :tenant_id`."""
    _require_tenant(model, tenant_id)
    stmt = select(*columns) if columns else select(model)
    return stmt.where(model.tenant_id == tenant_id)  # type: ignore[attr-defined]


def tcount(model: Any, tenant_id: str) -> Select:
    _require_tenant(model, tenant_id)
    return select(func.count()).select_from(model).where(model.tenant_id == tenant_id)


def tupdate(model: Any, tenant_id: str):
    _require_tenant(model, tenant_id)
    return update(model).where(model.tenant_id == tenant_id)


def tdelete(model: Any, tenant_id: str):
    _require_tenant(model, tenant_id)
    return delete(model).where(model.tenant_id == tenant_id)


async def tget(db: AsyncSession, model: type[T], tenant_id: str, **filters: Any) -> T | None:
    stmt = tq(model, tenant_id)
    for key, value in filters.items():
        stmt = stmt.where(getattr(model, key) == value)
    return (await db.execute(stmt.limit(1))).scalar_one_or_none()

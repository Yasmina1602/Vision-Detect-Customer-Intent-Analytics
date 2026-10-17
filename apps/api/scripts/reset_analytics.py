"""Analitika ma'lumotlarini 0 ga tushirish (katalog, do'kon, foydalanuvchilar va sozlamalar SAQLANADI).

python scripts/reset_analytics.py                  # nimalar o'chishini ko'rsatadi (hech narsa o'chirmaydi)
python scripts/reset_analytics.py --yes            # barcha do'konlar uchun o'chiradi
python scripts/reset_analytics.py --yes --tenant demo-shop
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import delete, func, select, update  # noqa: E402

from app.db.session import SessionLocal, engine  # noqa: E402
from app.models import (AiModel, CartSession, CatalogProduct, CatalogSyncRun, CustomerProfile, DailyStat, Event,  # noqa: E402
                        IdentityLink, ShopperSession, Tenant, UnmetDemandCluster, VisualSearch, WebhookDelivery)

ANALYTICS = [Event, VisualSearch, CartSession, ShopperSession, IdentityLink, UnmetDemandCluster, DailyStat,
             WebhookDelivery, CatalogSyncRun, CustomerProfile]


async def main(yes: bool, slug: str | None) -> None:
    async with SessionLocal() as db:
        tenant_id = None
        if slug:
            tenant_id = (await db.execute(select(Tenant.id).where(Tenant.slug == slug))).scalar_one_or_none()
            if not tenant_id:
                sys.exit(f"Do'kon topilmadi: {slug}")
        for model in ANALYTICS:
            q = select(func.count()).select_from(model)
            if tenant_id:
                q = q.where(model.tenant_id == tenant_id)
            n = (await db.execute(q)).scalar_one()
            print(f"  {model.__tablename__:<24} {n:>8} qator" + (" → 0" if yes else ""))
            if yes:
                d = delete(model)
                await db.execute(d.where(model.tenant_id == tenant_id) if tenant_id else d)
        if yes:
            p = update(CatalogProduct).values(popularity=0)
            await db.execute(p.where(CatalogProduct.tenant_id == tenant_id) if tenant_id else p)
            if not tenant_id:
                await db.execute(update(AiModel).values(success_count=0, error_count=0, last_error=None, cooldown_until=None))
            await db.commit()
            print("\nTayyor: analitika 0 ga tushirildi. Katalog, buyurtmalar, mijozlar va sozlamalar saqlandi.")
        else:
            print("\nHech narsa o'chirilmadi. Tasdiqlash uchun: --yes")
    await engine.dispose()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--tenant")
    a = ap.parse_args()
    asyncio.run(main(a.yes, a.tenant))

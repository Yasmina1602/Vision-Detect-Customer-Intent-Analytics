"""Demo do'kon (Premium) + katalog. FAQAT dev.

python scripts/seed_demo.py                  # yaratadi; mavjud bo'lsa faqat katalog va rasmlarni yangilaydi
python scripts/seed_demo.py --with-history   # + 30 kunlik SINTETIK analitika (faqat dashboard'ni ko'rsatish uchun)
python scripts/seed_demo.py --reset          # demo do'konni butunlay o'chirib qaytadan yaratadi

Analitika ma'lumoti default holatda YARATILMAYDI — dashboard haqiqiy hodisalar bilan to'ladi.
"""
import argparse
import asyncio
import random
import shutil
import sys
import uuid
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows konsoli (cp1251)

from sqlalchemy import delete, select  # noqa: E402

from app.core.config import ROOT_DIR, settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import utcnow  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models import (ApiKey, AuditLog, Campaign, Cart, CartSession, CatalogProduct, CatalogSyncRun,  # noqa: E402
                        Customer, CustomerProfile, DailyStat, Event, IdentityLink, Order, Payment, ShopperSession,
                        Tenant, TenantMembership, UnmetDemandCluster, User, VisualSearch, WebhookDelivery)
from app.services.catalog.sync import upsert_products  # noqa: E402
from app.services.matching.normalizer import make_demand_key  # noqa: E402
from app.services.tenants import create_tenant_with_key  # noqa: E402
from app.services.vision.prompts import PROMPT_VERSION  # noqa: E402

DEMO_EMAIL = "demo@vision.uz"
DEMO_PASSWORD = "Demo12345"
API = settings.PUBLIC_API_URL.rstrip("/")
STORE = settings.STOREFRONT_URL.rstrip("/")

HEX = {"qizil": "#dc2626", "qora": "#1f2937", "oq": "#e5e7eb", "ko'k": "#2563eb", "kulrang": "#9ca3af",
       "jigarrang": "#92400e", "pushti": "#ec4899", "yashil": "#16a34a", "bej": "#d6c7a1", "sariq": "#eab308",
       "to'q ko'k": "#1e3a8a", "binafsha": "#7c3aed", "to'q sariq": "#f97316"}

# (id, nom, kategoriya, rang, tur, narx so'm, eski narx so'm|None, zaxira dona, brend)
PRODUCTS = [
    ("101", "Qizil sport krossovka Runner", "poyabzal", "qizil", "krossovka", 489000, 590000, 14, "Stride"),
    ("102", "Qora krossovka Urban", "poyabzal", "qora", "krossovka", 529000, None, 22, "Stride"),
    ("103", "Oq klassik krossovka", "poyabzal", "oq", "krossovka", 459000, None, 30, "Nordic"),
    ("106", "Ko'k yugurish krossovkasi Air", "poyabzal", "ko'k", "krossovka", 559000, 649000, 9, "Stride"),
    ("104", "Jigarrang charm tufli", "poyabzal", "jigarrang", "tufli", 690000, None, 7, "Oxford & Co"),
    ("105", "Qora qishki etik", "poyabzal", "qora", "etik", 820000, None, 0, "Nordic"),
    ("201", "Qora xudi Oversize", "kiyim", "qora", "xudi", 349000, 420000, 25, "Urban Lab"),
    ("202", "Kulrang xudi Basic", "kiyim", "kulrang", "xudi", 299000, None, 18, "Urban Lab"),
    ("208", "Yashil xudi Campus", "kiyim", "yashil", "xudi", 329000, None, 11, "Urban Lab"),
    ("203", "Oq futbolka paxta", "kiyim", "oq", "futbolka", 129000, None, 60, "Basics"),
    ("209", "Qora futbolka Logo", "kiyim", "qora", "futbolka", 149000, 179000, 40, "Basics"),
    ("204", "Ko'k jinsi shim Slim", "kiyim", "ko'k", "shim", 399000, None, 16, "Denim Co"),
    ("205", "To'q ko'k kurtka", "kiyim", "to'q ko'k", "kurtka", 890000, 1090000, 6, "Nordic"),
    ("206", "Pushti ko'ylak yozgi", "kiyim", "pushti", "ko'ylak", 279000, None, 12, "Bloom"),
    ("207", "Bej sviter trikotaj", "kiyim", "bej", "sviter", 319000, None, 15, "Bloom"),
    ("210", "Jigarrang klassik kostyum", "kiyim", "jigarrang", "kostyum", 1490000, None, 4, "Oxford & Co"),
    ("301", "Qora charm sumka", "sumka", "qora", "sumka", 590000, 690000, 8, "Leatherline"),
    ("303", "Qizil ayollar sumkasi", "sumka", "qizil", "sumka", 450000, None, 10, "Leatherline"),
    ("302", "Kulrang ryukzak shahar", "sumka", "kulrang", "ryukzak", 359000, None, 20, "Trek"),
    ("401", "Kumush smart soat", "aksessuar", "kulrang", "soat", 1290000, 1490000, 5, "Pulse"),
    ("402", "Qora quyosh ko'zoynagi", "aksessuar", "qora", "ko'zoynak", 189000, None, 26, "Sunly"),
    ("403", "Bej kepka", "aksessuar", "bej", "kepka", 99000, None, 35, "Basics"),
    ("501", "Oq simsiz quloqchin", "elektronika", "oq", "naushnik", 459000, 520000, 19, "Pulse"),
    ("502", "Qora smartfon g'ilofi", "elektronika", "qora", "telefon", 99000, None, 50, "Pulse"),
]

UNMET = [("kiyim", "sariq", "xudi", "sariq xudi", 9), ("sumka", "yashil", "ryukzak", "yashil ryukzak", 6),
         ("poyabzal", "oq", "etik", "oq etik", 5), ("kiyim", "binafsha", "kurtka", "binafsha kurtka", 4),
         ("aksessuar", "qizil", "kepka", "qizil kepka", 3), ("poyabzal", "pushti", "krossovka", "pushti krossovka", 4)]

DESCRIPTIONS = {
    "krossovka": "Yengil va nafas oluvchi ust qismi, yumshoq taglik. Kundalik yurish va sport uchun.",
    "tufli": "Tabiiy charm, klassik dizayn. Ofis va tadbirlar uchun.",
    "etik": "Issiq astar, sirpanmaydigan taglik. Qishki sovuq uchun.",
    "xudi": "Yumshoq paxta-flis, kapyushon va old cho'ntak. Erkin bichim.",
    "futbolka": "100% paxta, mustahkam tikuv. Har kungi kiyim uchun.",
    "shim": "Elastik denim, zamonaviy slim bichim.",
    "kurtka": "Shamoldan himoya, suv o'tkazmaydigan qoplama, issiq astar.",
    "ko'ylak": "Yengil mato, yozgi kunlar uchun qulay.",
    "sviter": "Trikotaj to'qima, issiq va yumshoq.",
    "kostyum": "Klassik ikki qismli kostyum, nafis bichim.",
    "sumka": "Sifatli material, ichki cho'ntaklar, mustahkam tutqich.",
    "ryukzak": "Noutbuk bo'limi, suvga chidamli mato, qulay yelka kamarlari.",
    "soat": "Yurak urishi, qadamlar, uyqu monitoringi. Batareya 7 kungacha.",
    "ko'zoynak": "UV400 himoya, yengil ramka.",
    "kepka": "Sozlanadigan o'lcham, nafas oluvchi mato.",
    "naushnik": "Shovqinni pasaytirish, 24 soatgacha ishlash, tez quvvatlash.",
    "telefon": "Zarbaga chidamli silikon, aniq teshiklar.",
}


DEMO_IMAGES = Path(__file__).resolve().parents[1] / "app" / "demo" / "products"


def write_images(tenant_id: str) -> dict[str, str]:
    """Har mahsulot rasmi: app/demo/products/<id>.jpg → /media/<tenant>/demo-<id>.jpg (nisbiy yo'l)."""
    folder = settings.media_path / tenant_id
    folder.mkdir(parents=True, exist_ok=True)
    paths = {}
    for pid, *_ in PRODUCTS:
        shutil.copyfile(DEMO_IMAGES / f"{pid}.jpg", folder / f"demo-{pid}.jpg")
        paths[pid] = f"/media/{tenant_id}/demo-{pid}.jpg"
    return paths


def write_storefront_env(public_key: str) -> None:
    env = ROOT_DIR / "apps" / "storefront" / ".env.local"
    env.parent.mkdir(parents=True, exist_ok=True)
    env.write_text(f"NEXT_PUBLIC_STORE_KEY={public_key}\nAPI_INTERNAL_URL={API}\nNEXT_PUBLIC_API_URL={API}\n", encoding="utf-8")


async def reset(db) -> None:
    t = (await db.execute(select(Tenant).where(Tenant.slug == "demo-shop"))).scalar_one_or_none()
    if not t:
        return
    for model in (Event, VisualSearch, CartSession, CatalogProduct, CatalogSyncRun, ShopperSession, IdentityLink,
                  WebhookDelivery, UnmetDemandCluster, DailyStat, CustomerProfile, Campaign, Payment, Order, Cart,
                  Customer, ApiKey, TenantMembership, AuditLog):
        await db.execute(delete(model).where(model.tenant_id == t.id))
    await db.delete(t)
    await db.commit()
    print("Eski demo do'kon o'chirildi")


async def main(do_reset: bool, with_history: bool) -> None:
    random.seed(42)
    async with SessionLocal() as db:
        if do_reset:
            await reset(db)
        tenant = (await db.execute(select(Tenant).where(Tenant.slug == "demo-shop"))).scalar_one_or_none()
        secret = whsec = None
        if tenant:
            key = (await db.execute(select(ApiKey).where(ApiKey.tenant_id == tenant.id, ApiKey.revoked_at.is_(None))
                                    .limit(1))).scalar_one()
            print("Demo do'kon mavjud — katalog va rasmlar yangilanmoqda…")
        else:
            user = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one_or_none()
            if not user:
                user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), full_name="Demo Do'kon Egasi")
                db.add(user)
                await db.flush()
            tenant, (key, secret, whsec) = await create_tenant_with_key(db, "Demo Shop", plan="premium")
            tenant.slug = "demo-shop"
            tenant.platform = "html"
            # faqat yangi yaratilganda; mavjud tarifga tegilmaydi. Basic edition'da do'kon oddiy tarifda bo'ladi
            tenant.plan, tenant.catalog_mode = ("basic", "feed") if settings.is_basic_edition else ("premium", "hosted")
            db.add(TenantMembership(user_id=user.id, tenant_id=tenant.id, role="owner"))
        tenant.settings = {**(tenant.settings or {}), "thank_you_url_pattern": "/demo/vanilla/thanks",
                           "store_tagline": "Rasmdan toping — bir zumda xarid qiling",
                           "customer_deeplink": f"{settings.DASHBOARD_URL}/customers?ref={{customer_ref}}"}

        images = write_images(tenant.id)
        rows = [{"id": pid, "name": name, "category": cat, "color": color, "attributes": {"type": typ},
                 "price_minor": price * 100, "compare_at_minor": old * 100 if old else None, "stock_qty": stock,
                 "brand": brand, "currency": "UZS", "image_url": images[pid], "in_stock": stock > 0,
                 "product_url": f"{STORE}/product/{pid}", "description": DESCRIPTIONS.get(typ, name)}
                for pid, name, cat, color, typ, price, old, stock, brand in PRODUCTS]
        run = await upsert_products(db, tenant.id, rows, full_snapshot=True, source="manual")
        await db.flush()
        if with_history:
            await seed_history(db, tenant.id)
        await db.commit()
        write_storefront_env(key.public_key)

        print("\n[OK] Demo tayyor")
        print(f"   Katalog          : {run.items_seen} mahsulot ({run.items_changed} yangilandi)")
        print(f"   Dashboard        : {settings.DASHBOARD_URL}  ({DEMO_EMAIL} / {DEMO_PASSWORD})")
        print(f"   Storefront       : {STORE}")
        print(f"   Demo HTML sayt   : {API}/demo/vanilla")
        print(f"   Public key       : {key.public_key}")
        if secret:
            print(f"   Secret key       : {secret}   (faqat hozir ko'rsatiladi)")
            print(f"   Webhook secret   : {whsec}")
        print("   apps/storefront/.env.local yozildi")
    await engine.dispose()


async def seed_history(db, tenant_id: str) -> None:
    """SINTETIK tarix — faqat demo/prezentatsiya uchun. reset_analytics.py bilan o'chiriladi."""
    now = utcnow()
    catalog = [(pid, name, cat, color, typ, price * 100) for pid, name, cat, color, typ, price, *_ in PRODUCTS]
    searches = carts = 0
    for day in range(30, -1, -1):
        base = now - timedelta(days=day)
        n = int(random.randint(18, 40) * (1.25 if base.weekday() >= 5 else 1) * (1 + (30 - day) / 60))
        for _ in range(n):
            ts = base.replace(hour=random.randint(4, 17), minute=random.randint(0, 59), second=random.randint(0, 59))
            if ts > now:
                ts = now - timedelta(minutes=random.randint(1, 120))
            sid = f"vd_{uuid.uuid4().hex[:20]}"
            cref = f"u_{random.randint(1000, 1300)}" if random.random() < 0.3 else None
            db.add(ShopperSession(id=sid, tenant_id=tenant_id, first_seen=ts, last_seen=ts, consent=True,
                                  device=random.choice(["mobile", "mobile", "desktop"])))
            if cref:
                db.add(IdentityLink(tenant_id=tenant_id, session_id=sid, customer_ref=cref, linked_at=ts))
            unmet = random.random() < 0.22
            if unmet:
                cat, color, typ, query, _w = random.choices(UNMET, weights=[u[4] for u in UNMET])[0]
                pid = name = price = None
            else:
                pid, name, cat, color, typ, price = random.choice(catalog)
                query = f"{color} {typ}"
            search_id = str(uuid.uuid4())
            searches += 1
            db.add(VisualSearch(
                id=search_id, tenant_id=tenant_id, session_id=sid, customer_ref=cref,
                image_hash=uuid.uuid4().hex + uuid.uuid4().hex, prompt_version=PROMPT_VERSION,
                ai_detected={"category": cat, "color": color, "type": typ, "style": None, "tags": [color, typ],
                             "search_query": query, "confidence": round(random.uniform(0.7, 0.97), 2)},
                model_used="synthetic", best_score=round(random.uniform(0.18, 0.42) if unmet else random.uniform(0.55, 0.93), 3),
                results_count=0 if unmet else random.randint(2, 6), is_unmet_demand=unmet,
                demand_key=make_demand_key(cat, color, typ) if unmet else None,
                latency_ms=random.randint(1400, 3900), from_cache=random.random() < 0.12, created_at=ts))

            def ev(typ_, t, **kw):
                db.add(Event(event_id=str(uuid.uuid4()), tenant_id=tenant_id, session_id=sid, customer_ref=cref,
                             search_id=search_id, type=typ_, source="widget", ts=t, **kw))

            ev("SEARCH", ts)
            if unmet or random.random() > 0.9:
                continue
            ev("RESULT_VIEW", ts + timedelta(seconds=3))
            if random.random() > 0.55:
                continue
            ev("PRODUCT_CLICK", ts + timedelta(seconds=20), product_external_id=pid, price_minor=price, currency="UZS")
            if random.random() > 0.45:
                continue
            t_cart = ts + timedelta(minutes=random.randint(1, 8))
            qty = random.choice([1, 1, 1, 2])
            ev("ADD_TO_CART", t_cart, product_external_id=pid, qty=qty, price_minor=price, currency="UZS")
            carts += 1
            bought = random.random() < 0.42
            state = "purchased" if bought else ("abandoned" if (now - t_cart).total_seconds() > 86400 else "open")
            db.add(CartSession(tenant_id=tenant_id, session_id=sid, customer_ref=cref, search_id=search_id,
                               items=[{"id": pid, "qty": qty, "price_minor": price, "name": name}],
                               total_minor=price * qty, currency="UZS", state=state, last_activity_at=t_cart,
                               closed_at=(t_cart + timedelta(minutes=30)) if bought else
                               (t_cart + timedelta(hours=24) if state == "abandoned" else None)))
            if bought:
                db.add(Event(event_id=str(uuid.uuid4()), tenant_id=tenant_id, session_id=sid, customer_ref=cref,
                             search_id=search_id, type="PURCHASE", product_external_id=pid, qty=qty,
                             price_minor=price, currency="UZS", order_ref=f"SYN-{random.randint(10000, 99999)}",
                             source="webhook", ts=t_cart + timedelta(minutes=random.randint(5, 30))))
        await db.flush()
    print(f"   SINTETIK tarix: {searches} qidiruv, {carts} savat (30 kun)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--with-history", action="store_true")
    if not settings.is_dev:
        sys.exit("seed_demo faqat APP_ENV=development da ishlaydi")
    a = ap.parse_args()
    asyncio.run(main(a.reset, a.with_history))

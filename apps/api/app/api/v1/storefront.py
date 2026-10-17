"""Premium Storefront API (/v1/storefront/*).

Auth: X-Vision-Key (do'kon public key) — qaysi do'kon; ixtiyoriy Authorization: Bearer <customer token>.
Kuzatuv: X-VD-Session (vd_sid), X-VD-Search (rasm qidiruvidan kelgan bo'lsa search_id) — atribusiya uchun.
"""
import re
import uuid
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, public_tenant
from app.core.cache import hit_rate_limit
from app.core.errors import AppError, NotFound, Unauthorized
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.db.repositories import tq
from app.models import CatalogProduct, Customer, Order, Tenant
from app.services import storefront as sf
from app.services.events.identity import link_identity
from app.services.matching.embeddings import cosine

router = APIRouter(prefix="/v1/storefront", tags=["storefront (Premium)"])

SORTS = {
    "popular": (CatalogProduct.sales_count.desc(), CatalogProduct.popularity.desc()),
    "new": (CatalogProduct.updated_at.desc(),),
    "price_asc": (CatalogProduct.price_minor.asc(),),
    "price_desc": (CatalogProduct.price_minor.desc(),),
    "discount": (CatalogProduct.compare_at_minor.desc(),),
}


async def store_tenant(tenant: Tenant = Depends(public_tenant)) -> Tenant:
    if tenant.plan != "premium":
        raise AppError("PLAN_REQUIRED", "Storefront faqat Premium tarifda ishlaydi", 402)
    return tenant


async def optional_customer(tenant: Tenant = Depends(store_tenant), authorization: str | None = Header(default=None),
                            db: AsyncSession = Depends(get_db)) -> Customer | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    data = decode_token(authorization[7:], "customer")
    if not data or data.get("tid") != tenant.id:
        return None
    return await db.get(Customer, data["sub"])


async def required_customer(customer: Customer | None = Depends(optional_customer)) -> Customer:
    if not customer:
        raise Unauthorized("Hisobingizga kiring")
    return customer


def _sid(x_vd_session: str | None) -> str | None:
    return x_vd_session[:64] if x_vd_session and re.fullmatch(r"[A-Za-z0-9_\-]{8,64}", x_vd_session) else None


def _search(x_vd_search: str | None) -> str | None:
    try:
        return str(uuid.UUID(x_vd_search)) if x_vd_search else None
    except ValueError:
        return None


# ===================== katalog =====================
@router.get("/info")
async def info(tenant: Tenant = Depends(store_tenant), db: AsyncSession = Depends(get_db)):
    base = tq(CatalogProduct, tenant.id).where(CatalogProduct.is_deleted.is_(False))
    cats = (await db.execute(base.with_only_columns(CatalogProduct.category, func.count())
                             .group_by(CatalogProduct.category).order_by(func.count().desc()))).all()
    s = tenant.settings or {}
    return {
        "name": tenant.name, "slug": tenant.slug, "currency": tenant.setting("currency"),
        "theme": s.get("theme", {}), "tagline": s.get("store_tagline") or "Rasmdan toping — bir zumda xarid qiling",
        "phone": s.get("store_phone") or "+998 71 200 00 00", "address": s.get("store_address") or "Toshkent",
        "categories": [{"name": c or "boshqa", "count": n} for c, n in cats],
        "delivery": sf.delivery_rules(tenant),
        "payment_methods": [{"id": "cash", "label": "Naqd (yetkazganda)"}, {"id": "card", "label": "Bank kartasi (Uzcard/Humo)"},
                            {"id": "payme", "label": "Payme"}, {"id": "click", "label": "Click"}],
    }


@router.get("/products")
async def products(q: str = "", category: str | None = None, color: str | None = None, min_price: int | None = None,
                   max_price: int | None = None, in_stock: bool = False, sale: bool = False,
                   sort: Literal["popular", "new", "price_asc", "price_desc", "discount"] = "popular",
                   page: int = Query(1, ge=1), size: int = Query(24, ge=1, le=60),
                   ids: str | None = None, tenant: Tenant = Depends(store_tenant), db: AsyncSession = Depends(get_db)):
    stmt = tq(CatalogProduct, tenant.id).where(CatalogProduct.is_deleted.is_(False))
    if ids:
        stmt = stmt.where(CatalogProduct.external_id.in_(ids.split(",")[:60]))
    if q:
        like = f"%{q.strip()[:80]}%"
        stmt = stmt.where(or_(CatalogProduct.name.like(like), CatalogProduct.description.like(like),
                              CatalogProduct.category.like(like), CatalogProduct.color.like(like)))
    facet_base = stmt
    if category:
        stmt = stmt.where(CatalogProduct.category == category)
    if color:
        stmt = stmt.where(CatalogProduct.color == color)
    if min_price is not None:
        stmt = stmt.where(CatalogProduct.price_minor >= min_price)
    if max_price is not None:
        stmt = stmt.where(CatalogProduct.price_minor <= max_price)
    if in_stock:
        stmt = stmt.where(CatalogProduct.in_stock.is_(True))
    if sale:
        stmt = stmt.where(CatalogProduct.compare_at_minor > CatalogProduct.price_minor)
    total = (await db.execute(stmt.with_only_columns(func.count()))).scalar_one()
    rows = (await db.execute(stmt.order_by(CatalogProduct.in_stock.desc(), *SORTS[sort])
                             .offset((page - 1) * size).limit(size))).scalars().all()
    colors = (await db.execute(facet_base.with_only_columns(CatalogProduct.color, func.count())
                               .where(CatalogProduct.color.is_not(None)).group_by(CatalogProduct.color))).all()
    cats = (await db.execute(facet_base.with_only_columns(CatalogProduct.category, func.count())
                             .group_by(CatalogProduct.category))).all()
    pr = (await db.execute(facet_base.with_only_columns(func.min(CatalogProduct.price_minor), func.max(CatalogProduct.price_minor)))).one()
    return {"total": total, "page": page, "size": size, "items": [sf.product_public(p) for p in rows],
            "facets": {"colors": [{"name": c, "count": n} for c, n in colors],
                       "categories": [{"name": c or "boshqa", "count": n} for c, n in cats],
                       "price": {"min": pr[0] or 0, "max": pr[1] or 0}}}


@router.get("/products/{product_id}")
async def product(product_id: str, tenant: Tenant = Depends(store_tenant), db: AsyncSession = Depends(get_db)):
    p = (await db.execute(tq(CatalogProduct, tenant.id).where(
        CatalogProduct.external_id == product_id, CatalogProduct.is_deleted.is_(False)))).scalar_one_or_none()
    if not p:
        raise NotFound("Mahsulot topilmadi")
    pool = (await db.execute(tq(CatalogProduct, tenant.id).where(
        CatalogProduct.is_deleted.is_(False), CatalogProduct.id != p.id).limit(500))).scalars().all()
    similar = sorted(pool, key=lambda o: -(cosine(p.embedding, o.embedding) + (0.3 if o.category == p.category else 0)
                                          + (0.1 if o.in_stock else 0)))[:8]
    return {"product": sf.product_public(p), "similar": [sf.product_public(o) for o in similar]}


# ===================== savat =====================
class CartItemIn(BaseModel):
    product_id: str = Field(min_length=1, max_length=191)
    qty: int = Field(default=1, ge=0, le=99)


@router.get("/cart")
async def get_cart(cart_id: str | None = None, delivery: Literal["courier", "pickup"] = "courier",
                   tenant: Tenant = Depends(store_tenant), customer: Customer | None = Depends(optional_customer),
                   x_vd_session: str | None = Header(default=None), db: AsyncSession = Depends(get_db)):
    cart = await sf.get_cart(db, tenant, cart_id, _sid(x_vd_session), customer.id if customer else None, create=False)
    return await sf.cart_view(db, tenant, cart, delivery)


@router.post("/cart/items")
async def add_to_cart(body: CartItemIn, cart_id: str | None = None, tenant: Tenant = Depends(store_tenant),
                      customer: Customer | None = Depends(optional_customer), db: AsyncSession = Depends(get_db),
                      x_vd_session: str | None = Header(default=None), x_vd_search: str | None = Header(default=None)):
    sid = _sid(x_vd_session)
    cart = await sf.get_cart(db, tenant, cart_id, sid, customer.id if customer else None)
    await sf.set_item(db, tenant, cart, body.product_id, max(body.qty, 1), add=True, session_id=sid,
                      customer_ref=customer.customer_ref if customer else None, search_id=_search(x_vd_search))
    await db.flush()
    return await sf.cart_view(db, tenant, cart)


@router.put("/cart/items")
async def update_cart_item(body: CartItemIn, cart_id: str, tenant: Tenant = Depends(store_tenant),
                           customer: Customer | None = Depends(optional_customer), db: AsyncSession = Depends(get_db),
                           x_vd_session: str | None = Header(default=None)):
    sid = _sid(x_vd_session)
    cart = await sf.get_cart(db, tenant, cart_id, sid, customer.id if customer else None, create=False)
    if not cart:
        raise NotFound("Savat topilmadi")
    await sf.set_item(db, tenant, cart, body.product_id, body.qty, add=False, session_id=sid,
                      customer_ref=customer.customer_ref if customer else None, search_id=None)
    await db.flush()
    return await sf.cart_view(db, tenant, cart)


# ===================== checkout va to'lov =====================
class CheckoutIn(BaseModel):
    cart_id: str = Field(min_length=10, max_length=36)
    name: str = Field(min_length=2, max_length=200)
    phone: str = Field(min_length=7, max_length=32)
    email: EmailStr | None = None
    city: str = Field(default="Toshkent", max_length=100)
    address: str | None = Field(default=None, max_length=500)
    delivery_method: Literal["courier", "pickup"] = "courier"
    payment_method: Literal["cash", "card", "payme", "click"] = "cash"
    note: str | None = Field(default=None, max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=64)

    @field_validator("email", mode="before")
    @classmethod
    def _empty_email(cls, v):
        return v or None


@router.post("/checkout")
async def checkout(body: CheckoutIn, tenant: Tenant = Depends(store_tenant),
                   customer: Customer | None = Depends(optional_customer), db: AsyncSession = Depends(get_db),
                   x_vd_session: str | None = Header(default=None), x_vd_search: str | None = Header(default=None)):
    if await hit_rate_limit(f"checkout:{x_vd_session or body.phone}", 10):
        raise AppError("RATE_LIMITED", "Juda ko'p urinish", 429)
    order = await sf.checkout(db, tenant, body.model_dump(), session_id=_sid(x_vd_session), customer=customer,
                              search_id=_search(x_vd_search))
    await db.flush()
    view = await sf.order_view(db, order, with_token=True)
    view["requires_payment"] = order.payment_method in sf.ONLINE_METHODS and order.payment_status != "paid"
    return view


async def _order_for(db: AsyncSession, tenant: Tenant, number: str, token: str | None,
                     customer: Customer | None) -> Order:
    order = (await db.execute(tq(Order, tenant.id).where(Order.number == number))).scalar_one_or_none()
    if not order:
        raise NotFound("Buyurtma topilmadi")
    if not (sf.verify_order_token(order.id, token) or (customer and order.customer_id == customer.id)):
        raise NotFound("Buyurtma topilmadi")
    return order


@router.get("/orders/{number}")
async def get_order(number: str, t: str | None = None, tenant: Tenant = Depends(store_tenant),
                    customer: Customer | None = Depends(optional_customer), db: AsyncSession = Depends(get_db)):
    order = await _order_for(db, tenant, number, t, customer)
    return await sf.order_view(db, order, with_token=True)


class PayIn(BaseModel):
    token: str | None = None
    card_number: str = Field(min_length=12, max_length=25)
    expiry: str = Field(min_length=5, max_length=5)


@router.post("/orders/{number}/pay")
async def pay(number: str, body: PayIn, tenant: Tenant = Depends(store_tenant),
              customer: Customer | None = Depends(optional_customer), db: AsyncSession = Depends(get_db)):
    if await hit_rate_limit(f"pay:{number}", 6):
        raise AppError("RATE_LIMITED", "Juda ko'p urinish. Bir daqiqadan so'ng qayta urinib ko'ring.", 429)
    order = await _order_for(db, tenant, number, body.token, customer)
    payment = await sf.pay_with_test_card(db, tenant, order, body.card_number, body.expiry)
    await db.flush()
    view = await sf.order_view(db, order, with_token=True)
    view["payment_result"] = {"status": payment.status, "error": payment.error}
    return view


@router.post("/orders/{number}/cancel")
async def cancel(number: str, t: str | None = None, tenant: Tenant = Depends(store_tenant),
                 customer: Customer | None = Depends(optional_customer), db: AsyncSession = Depends(get_db)):
    order = await _order_for(db, tenant, number, t, customer)
    if order.status != "new":
        raise AppError("CANNOT_CANCEL", "Buyurtma allaqachon tasdiqlangan — do'kon bilan bog'laning", 409)
    await sf.change_status(db, tenant, order, "cancelled")
    return await sf.order_view(db, order, with_token=True)


# ===================== xaridor hisobi =====================
class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    marketing_consent: bool = False


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


def _customer_out(c: Customer) -> dict:
    return {"id": c.id, "full_name": c.full_name, "email": c.email, "phone": c.phone, "city": c.city,
            "address": c.address, "marketing_consent": c.marketing_consent}


def _token(c: Customer) -> str:
    return create_token(c.id, "customer", timedelta(days=30), {"tid": c.tenant_id})


@router.post("/auth/register")
async def register(body: RegisterIn, tenant: Tenant = Depends(store_tenant), db: AsyncSession = Depends(get_db),
                   x_vd_session: str | None = Header(default=None)):
    email = body.email.lower()
    if (await db.execute(tq(Customer, tenant.id).where(Customer.email == email))).scalar_one_or_none():
        raise AppError("EMAIL_TAKEN", "Bu e-mail bilan hisob mavjud", 409)
    c = Customer(tenant_id=tenant.id, email=email, full_name=body.full_name,
                 phone=sf.normalize_phone(body.phone) if body.phone else None,
                 password_hash=hash_password(body.password), marketing_consent=body.marketing_consent)
    db.add(c)
    await db.flush()
    if sid := _sid(x_vd_session):
        await link_identity(db, tenant.id, sid, c.customer_ref)
    return {"token": _token(c), "customer": _customer_out(c)}


@router.post("/auth/login")
async def login(body: LoginIn, tenant: Tenant = Depends(store_tenant), db: AsyncSession = Depends(get_db),
                x_vd_session: str | None = Header(default=None)):
    if await hit_rate_limit(f"clogin:{body.email}", 10):
        raise AppError("RATE_LIMITED", "Juda ko'p urinish", 429)
    c = (await db.execute(tq(Customer, tenant.id).where(Customer.email == body.email.lower()))).scalar_one_or_none()
    if not c or not verify_password(body.password, c.password_hash):
        raise AppError("INVALID_CREDENTIALS", "E-mail yoki parol noto'g'ri", 401)
    if sid := _sid(x_vd_session):
        await link_identity(db, tenant.id, sid, c.customer_ref)
    return {"token": _token(c), "customer": _customer_out(c)}


@router.get("/me")
async def me(customer: Customer = Depends(required_customer), db: AsyncSession = Depends(get_db)):
    orders = (await db.execute(select(Order).where(Order.customer_id == customer.id)
                               .order_by(Order.created_at.desc()).limit(50))).scalars().all()
    return {"customer": _customer_out(customer), "orders": [
        {"number": o.number, "status": o.status, "status_label": sf.STATUS_LABELS.get(o.status),
         "payment_status": o.payment_status, "total_minor": o.total_minor, "currency": o.currency,
         "created_at": o.created_at, "token": sf.order_token(o.id)} for o in orders]}


class ProfileIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=500)
    marketing_consent: bool | None = None


@router.patch("/me")
async def update_me(body: ProfileIn, customer: Customer = Depends(required_customer)):
    data = body.model_dump(exclude_none=True)
    if "phone" in data:
        data["phone"] = sf.normalize_phone(data["phone"])
    for k, v in data.items():
        setattr(customer, k, v)
    return {"customer": _customer_out(customer)}


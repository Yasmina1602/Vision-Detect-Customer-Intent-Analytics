"""Premium Storefront: savat, checkout, to'lov va buyurtma holatlari.

Qoidalar (README 15-bo'lim):
- Narx HAR DOIM serverda qayta hisoblanadi (klientdan kelgan narxga ishonilmaydi).
- Zaxira tranzaksiyada kamaytiriladi: SELECT ... FOR UPDATE (bir vaqtda ikki xaridor oxirgi donani ololmaydi).
- Checkout idempotent: bir xil idempotency_key bilan qayta yuborilsa, yangi buyurtma yaratilmaydi.
- To'lov callback'i idempotent: allaqachon to'langan to'lov qayta o'tkazilmaydi.
- Analitikaga boshqa saytlar kabi oddiy hodisa ketadi (source='storefront').
"""
import hashlib
import hmac
import logging
import random
import re
import string
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, NotFound
from app.db.base import utcnow
from app.db.repositories import tq
from app.models import Cart, CartItem, CatalogProduct, Customer, Order, OrderItem, Payment, Tenant
from app.services.events.collector import EventIn, EventItem, ingest
from app.services.events.identity import link_identity
from app.services.media import abs_url

log = logging.getLogger("app.storefront")

ONLINE_METHODS = ("card", "payme", "click")
STATUS_FLOW = {"new": ("confirmed", "cancelled"), "confirmed": ("shipped", "cancelled"),
               "shipped": ("delivered", "cancelled"), "delivered": (), "cancelled": ()}
STATUS_LABELS = {"new": "Yangi", "confirmed": "Tasdiqlandi", "shipped": "Yo'lda", "delivered": "Yetkazildi",
                 "cancelled": "Bekor qilindi"}


# ---------------- yordamchilar ----------------
def delivery_rules(tenant: Tenant) -> dict[str, int]:
    s = tenant.settings or {}
    return {"fee_minor": int(s.get("delivery_fee_minor", 2_500_000)),              # 25 000 so'm
            "free_from_minor": int(s.get("free_delivery_from_minor", 50_000_000))}  # 500 000 so'mdan bepul


def product_public(p: CatalogProduct) -> dict[str, Any]:
    attrs = p.attributes or {}
    discount = (round((1 - p.price_minor / p.compare_at_minor) * 100)
                if p.compare_at_minor and p.price_minor and p.compare_at_minor > p.price_minor else 0)
    return {
        "id": p.external_id, "uid": p.id, "name": p.name, "description": p.description, "brand": p.brand,
        "category": p.category, "color": p.color, "type": attrs.get("type"),
        "price_minor": p.price_minor, "compare_at_minor": p.compare_at_minor if discount else None,
        "discount_pct": discount, "currency": p.currency or "UZS",
        "image_url": abs_url(p.image_url), "images": [abs_url(i) for i in (p.images or [])] or ([abs_url(p.image_url)] if p.image_url else []),
        "in_stock": p.in_stock and (p.stock_qty is None or p.stock_qty > 0), "stock_qty": p.stock_qty,
        "sales_count": p.sales_count or 0, "attributes": {k: v for k, v in attrs.items() if k != "type"},
    }


def order_token(order_id: str) -> str:
    """Mehmon xaridor o'z buyurtmasini ko'rishi uchun imzo (login'siz)."""
    return hmac.new(settings.APP_SECRET_KEY.encode(), f"order:{order_id}".encode(), hashlib.sha256).hexdigest()[:24]


def verify_order_token(order_id: str, token: str | None) -> bool:
    return bool(token) and hmac.compare_digest(order_token(order_id), token)  # type: ignore[arg-type]


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 9:
        digits = "998" + digits
    if not (11 <= len(digits) <= 15):
        raise AppError("INVALID_PHONE", "Telefon raqami noto'g'ri (masalan +998 90 123 45 67)", 422)
    return "+" + digits


# ---------------- savat ----------------
async def get_cart(db: AsyncSession, tenant: Tenant, cart_id: str | None, session_id: str | None,
                   customer_id: str | None = None, create: bool = True) -> Cart | None:
    cart = None
    if cart_id:
        cart = (await db.execute(tq(Cart, tenant.id).where(Cart.id == cart_id))).scalar_one_or_none()
    if cart is None and customer_id:
        cart = (await db.execute(tq(Cart, tenant.id).where(Cart.customer_id == customer_id)
                                 .order_by(Cart.updated_at.desc()).limit(1))).scalar_one_or_none()
    if cart is None and create:
        cart = Cart(tenant_id=tenant.id, session_id=session_id, customer_id=customer_id, updated_at=utcnow())
        db.add(cart)
        await db.flush()
    if cart is not None:
        if customer_id and not cart.customer_id:
            cart.customer_id = customer_id
        if session_id and not cart.session_id:
            cart.session_id = session_id
    return cart


async def cart_view(db: AsyncSession, tenant: Tenant, cart: Cart | None, delivery_method: str = "courier") -> dict[str, Any]:
    if cart is None:
        return {"id": None, "items": [], "count": 0, "subtotal_minor": 0, "delivery_fee_minor": 0, "total_minor": 0,
                "currency": tenant.setting("currency"), **delivery_rules(tenant)}
    rows = (await db.execute(
        select(CartItem, CatalogProduct).join(CatalogProduct, CatalogProduct.id == CartItem.product_id)
        .where(CartItem.cart_id == cart.id, CatalogProduct.tenant_id == tenant.id))).all()
    items, subtotal, issues = [], 0, []
    for ci, p in rows:
        pub = product_public(p)
        available = pub["in_stock"] and not p.is_deleted
        max_qty = p.stock_qty if p.stock_qty is not None else 99
        line = (p.price_minor or 0) * ci.qty
        if available:
            subtotal += line
        else:
            issues.append(f"{p.name} hozir mavjud emas")
        items.append({"product": pub, "qty": ci.qty, "line_minor": line, "available": available,
                      "max_qty": max_qty, "price_changed": ci.price_minor != p.price_minor})
    rules = delivery_rules(tenant)
    fee = 0 if delivery_method == "pickup" or subtotal == 0 or subtotal >= rules["free_from_minor"] else rules["fee_minor"]
    return {"id": cart.id, "items": items, "count": sum(i["qty"] for i in items), "subtotal_minor": subtotal,
            "delivery_fee_minor": fee, "total_minor": subtotal + fee, "currency": tenant.setting("currency"),
            "issues": issues, **rules}


async def _product_by_public_id(db: AsyncSession, tenant: Tenant, product_id: str) -> CatalogProduct:
    p = (await db.execute(tq(CatalogProduct, tenant.id).where(
        (CatalogProduct.external_id == product_id) | (CatalogProduct.id == product_id),
        CatalogProduct.is_deleted.is_(False)).limit(1))).scalar_one_or_none()
    if not p:
        raise NotFound("Mahsulot topilmadi")
    return p


async def set_item(db: AsyncSession, tenant: Tenant, cart: Cart, product_id: str, qty: int, *, add: bool,
                   session_id: str | None, customer_ref: str | None, search_id: str | None) -> None:
    p = await _product_by_public_id(db, tenant, product_id)
    item = await db.get(CartItem, (cart.id, p.id))
    old_qty = item.qty if item else 0
    new_qty = old_qty + qty if add else qty
    if new_qty > 0 and not (p.in_stock and (p.stock_qty is None or p.stock_qty > 0)):
        raise AppError("OUT_OF_STOCK", "Mahsulot tugagan", 409)
    if p.stock_qty is not None and new_qty > p.stock_qty:
        raise AppError("NOT_ENOUGH_STOCK", f"Omborda faqat {p.stock_qty} dona bor", 409)
    if new_qty > 99:
        raise AppError("QTY_LIMIT", "Bitta mahsulotdan ko'pi bilan 99 dona", 422)

    if new_qty <= 0:
        if item:
            await db.delete(item)
    elif item:
        item.qty, item.price_minor = new_qty, p.price_minor or 0
    else:
        db.add(CartItem(cart_id=cart.id, product_id=p.id, qty=new_qty, price_minor=p.price_minor or 0))
    cart.updated_at = utcnow()

    diff = new_qty - old_qty
    if diff and session_id:
        await ingest(db, tenant, EventIn(
            event_id=uuid.uuid4(), type="ADD_TO_CART" if diff > 0 else "REMOVE_FROM_CART", session_id=session_id,
            customer_ref=customer_ref, search_id=uuid.UUID(search_id) if search_id else None,
            product_id=p.external_id, qty=abs(diff), price_minor=p.price_minor, currency=p.currency), source="storefront")


# ---------------- checkout ----------------
async def _new_order_number(db: AsyncSession, tenant: Tenant) -> str:
    prefix = re.sub(r"[^A-Z]", "", tenant.slug.upper())[:3] or "VD"
    for _ in range(10):
        num = f"{prefix}-{utcnow():%y%m%d}-{''.join(random.choices(string.digits, k=4))}"
        if not (await db.execute(tq(Order, tenant.id, Order.id).where(Order.number == num))).first():
            return num
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


async def checkout(db: AsyncSession, tenant: Tenant, data: dict[str, Any], *, session_id: str | None,
                   customer: Customer | None, search_id: str | None) -> Order:
    idem = data.get("idempotency_key")
    if idem:
        existing = (await db.execute(tq(Order, tenant.id).where(Order.idempotency_key == idem))).scalar_one_or_none()
        if existing:
            return existing

    cart = await get_cart(db, tenant, data.get("cart_id"), session_id, customer.id if customer else None, create=False)
    if cart is None:
        raise AppError("CART_EMPTY", "Savat bo'sh", 409)
    items = (await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))).scalars().all()
    if not items:
        raise AppError("CART_EMPTY", "Savat bo'sh", 409)

    # Zaxirani bloklash — tranzaksiya oxirigacha boshqa checkout bu qatorlarni o'zgartira olmaydi
    locked = {p.id: p for p in (await db.execute(
        tq(CatalogProduct, tenant.id).where(CatalogProduct.id.in_([i.product_id for i in items])).with_for_update()
    )).scalars().all()}

    problems, subtotal, lines = [], 0, []
    for ci in items:
        p = locked.get(ci.product_id)
        if not p or p.is_deleted or not p.in_stock:
            problems.append(f"{p.name if p else 'Mahsulot'} tugagan")
            continue
        if p.stock_qty is not None and p.stock_qty < ci.qty:
            problems.append(f"{p.name}: omborda faqat {p.stock_qty} dona")
            continue
        price = p.price_minor or 0
        subtotal += price * ci.qty
        lines.append((ci, p, price))
    if problems:
        raise AppError("STOCK_CHANGED", "; ".join(problems), 409, {"problems": problems})

    method = data["payment_method"]
    delivery = data["delivery_method"]
    rules = delivery_rules(tenant)
    fee = 0 if delivery == "pickup" or subtotal >= rules["free_from_minor"] else rules["fee_minor"]
    currency = tenant.setting("currency")

    order = Order(
        tenant_id=tenant.id, customer_id=customer.id if customer else None,
        number=await _new_order_number(db, tenant), status="new", payment_status="pending",
        payment_method=method, delivery_method=delivery, customer_name=data["name"].strip(),
        phone=normalize_phone(data["phone"]), email=(data.get("email") or None),
        city=data.get("city"), address=data.get("address") if delivery == "courier" else None,
        note=data.get("note"), subtotal_minor=subtotal, discount_minor=0, delivery_fee_minor=fee,
        total_minor=subtotal + fee, currency=currency, search_id=search_id, session_id=session_id,
        idempotency_key=idem, created_at=utcnow(),
    )
    if delivery == "courier" and not order.address:
        raise AppError("ADDRESS_REQUIRED", "Yetkazib berish manzilini kiriting", 422)
    db.add(order)
    await db.flush()

    for ci, p, price in lines:
        db.add(OrderItem(order_id=order.id, product_id=p.id, product_external_id=p.external_id, name=p.name,
                         image_url=p.image_url, qty=ci.qty, price_minor=price))
        if p.stock_qty is not None:
            p.stock_qty -= ci.qty
            if p.stock_qty <= 0:
                p.in_stock = False
        p.sales_count = (p.sales_count or 0) + ci.qty
    db.add(Payment(tenant_id=tenant.id, order_id=order.id, provider=method, amount_minor=order.total_minor,
                   currency=currency, status="pending", created_at=utcnow()))
    await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))

    if customer:
        customer.city = customer.city or order.city
        customer.address = customer.address or order.address
        customer.phone = customer.phone or order.phone
        if session_id:
            await link_identity(db, tenant.id, session_id, customer.customer_ref)

    if method == "cash":               # naqd: buyurtma = xarid; to'lov yetkazishda
        await _emit_purchase(db, tenant, order, customer)
    return order


async def _emit_purchase(db: AsyncSession, tenant: Tenant, order: Order, customer: Customer | None) -> None:
    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    await ingest(db, tenant, EventIn(
        event_id=uuid.uuid5(uuid.NAMESPACE_URL, f"order:{order.id}"), type="PURCHASE", session_id=order.session_id,
        customer_ref=customer.customer_ref if customer else None, order_ref=order.number, currency=order.currency,
        search_id=uuid.UUID(order.search_id) if order.search_id else None,
        items=[EventItem(id=i.product_external_id or i.product_id, qty=i.qty, price_minor=i.price_minor, name=i.name)
               for i in items]), source="storefront")


# ---------------- to'lov (test shlyuz) ----------------
def luhn_ok(number: str) -> bool:
    digits = [int(d) for d in number][::-1]
    total = sum(d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2) for i, d in enumerate(digits))
    return total % 10 == 0


async def pay_with_test_card(db: AsyncSession, tenant: Tenant, order: Order, card: str, expiry: str) -> Payment:
    """Test shlyuz: Luhn tekshiruvidan o'tgan 16 xonali karta muvaffaqiyatli (masalan 4242 4242 4242 4242);
    4000 0000 0000 0002 — "mablag' yetarli emas" deb rad etiladi.
    Haqiqiy Payme/Click ulanishi uchun shu funksiya provayder API'si bilan almashtiriladi (callback idempotent)."""
    payment = (await db.execute(tq(Payment, tenant.id).where(Payment.order_id == order.id)
                                .order_by(Payment.created_at.desc()).limit(1).with_for_update())).scalar_one_or_none()
    if not payment:
        raise NotFound("To'lov topilmadi")
    if payment.status == "paid":
        return payment                      # idempotent
    if order.status == "cancelled":
        raise AppError("ORDER_CANCELLED", "Buyurtma bekor qilingan", 409)
    digits = re.sub(r"\D", "", card or "")
    if len(digits) != 16 or not luhn_ok(digits):
        raise AppError("INVALID_CARD", "Karta raqami noto'g'ri", 422)
    if not re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", expiry or ""):
        raise AppError("INVALID_EXPIRY", "Amal qilish muddati OO/YY formatida bo'lsin", 422)
    mm, yy = int(expiry[:2]), 2000 + int(expiry[3:])
    now = datetime.utcnow()
    if (yy, mm) < (now.year, now.month):
        raise AppError("CARD_EXPIRED", "Karta muddati o'tgan", 422)

    payment.card_mask = f"{digits[:4]} **** **** {digits[-4:]}"
    payment.external_id = f"test_{uuid.uuid4().hex[:16]}"
    if digits.endswith("0002"):
        payment.status, payment.error = "failed", "Karta rad etildi (mablag' yetarli emas)"
        order.payment_status = "failed"
        return payment
    payment.status, payment.error = "paid", None
    order.payment_status = "paid"
    if order.status == "new":
        order.status = "confirmed"
    customer = await db.get(Customer, order.customer_id) if order.customer_id else None
    await _emit_purchase(db, tenant, order, customer)
    return payment


# ---------------- holatlar ----------------
async def change_status(db: AsyncSession, tenant: Tenant, order: Order, new_status: str) -> None:
    if new_status == order.status:
        return
    if new_status not in STATUS_FLOW.get(order.status, ()):
        raise AppError("INVALID_TRANSITION",
                       f"'{STATUS_LABELS[order.status]}' holatidan '{STATUS_LABELS.get(new_status, new_status)}' ga o'tib bo'lmaydi", 409)
    if new_status == "cancelled":
        # zaxirani qaytarish
        items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
        prods = {p.id: p for p in (await db.execute(tq(CatalogProduct, tenant.id).where(
            CatalogProduct.id.in_([i.product_id for i in items])).with_for_update())).scalars().all()}
        for i in items:
            p = prods.get(i.product_id)
            if p:
                if p.stock_qty is not None:
                    p.stock_qty += i.qty
                    p.in_stock = True
                p.sales_count = max(0, (p.sales_count or 0) - i.qty)
        pay = (await db.execute(tq(Payment, tenant.id).where(Payment.order_id == order.id))).scalars().all()
        for p in pay:
            p.status = "refunded" if p.status == "paid" else "cancelled" if p.status == "pending" else p.status
        order.payment_status = "refunded" if order.payment_status == "paid" else "cancelled"
    if new_status == "delivered" and order.payment_method == "cash":
        order.payment_status = "paid"
        for p in (await db.execute(tq(Payment, tenant.id).where(Payment.order_id == order.id))).scalars().all():
            if p.status == "pending":
                p.status = "paid"
    order.status = new_status


async def order_view(db: AsyncSession, order: Order, with_token: bool = False) -> dict[str, Any]:
    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    payments = (await db.execute(select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at))).scalars().all()
    out = {
        "id": order.id, "number": order.number, "status": order.status, "status_label": STATUS_LABELS.get(order.status),
        "payment_status": order.payment_status, "payment_method": order.payment_method,
        "delivery_method": order.delivery_method, "customer_name": order.customer_name, "phone": order.phone,
        "email": order.email, "city": order.city, "address": order.address, "note": order.note,
        "subtotal_minor": order.subtotal_minor, "delivery_fee_minor": order.delivery_fee_minor,
        "discount_minor": order.discount_minor, "total_minor": order.total_minor, "currency": order.currency,
        "created_at": order.created_at, "updated_at": order.updated_at, "from_search": bool(order.search_id),
        "items": [{"product_id": i.product_external_id, "name": i.name, "image_url": abs_url(i.image_url), "qty": i.qty,
                   "price_minor": i.price_minor, "line_minor": i.price_minor * i.qty} for i in items],
        "payments": [{"id": p.id, "provider": p.provider, "status": p.status, "amount_minor": p.amount_minor,
                      "card_mask": p.card_mask, "error": p.error, "created_at": p.created_at} for p in payments],
        "next_statuses": list(STATUS_FLOW.get(order.status, ())),
    }
    if with_token:
        out["token"] = order_token(order.id)
    return out

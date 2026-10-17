"""Event Collector: idempotent qabul, last-touch atribusiya, savat sessiyalari."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.base import utcnow
from app.db.repositories import tq
from app.models import CartSession, CatalogProduct, Event, IdentityLink, ShopperSession, Tenant, VisualSearch
from app.services.events.identity import validate_customer_ref

EventType = Literal["SEARCH", "RESULT_VIEW", "PRODUCT_CLICK", "ADD_TO_CART", "REMOVE_FROM_CART", "PURCHASE"]


class EventItem(BaseModel):
    id: str = Field(min_length=1, max_length=191)
    qty: int = Field(default=1, ge=1, le=10_000)
    price_minor: int | None = Field(default=None, ge=0)
    name: str | None = Field(default=None, max_length=300)

    @field_validator("id", mode="before")
    @classmethod
    def _id(cls, v):
        return str(v)


class EventIn(BaseModel):
    event_id: uuid.UUID
    type: EventType
    session_id: str | None = Field(default=None, max_length=64)
    customer_ref: str | None = Field(default=None, max_length=128)
    search_id: uuid.UUID | None = None
    product_id: str | None = Field(default=None, max_length=191)
    qty: int = Field(default=1, ge=1, le=10_000)
    price_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    order_ref: str | None = Field(default=None, max_length=128)
    items: list[EventItem] | None = Field(default=None, max_length=200)
    ts: datetime | None = None

    @field_validator("product_id", "order_ref", mode="before")
    @classmethod
    def _str(cls, v):
        return str(v) if v is not None else None


def _clamp_ts(ts: datetime | None) -> datetime:
    now = utcnow()
    if ts is None:
        return now
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    if ts > now + timedelta(minutes=5) or ts < now - timedelta(days=7):
        return now
    return ts


async def touch_session(db: AsyncSession, tenant_id: str, session_id: str | None, consent: bool | None = None,
                        device: str | None = None) -> None:
    if not session_id:
        return
    now = utcnow()
    values: dict[str, Any] = {"id": session_id, "tenant_id": tenant_id, "first_seen": now, "last_seen": now,
                              "consent": bool(consent), "device": device}
    update: dict[str, Any] = {"last_seen": now}
    if consent is not None:
        update["consent"] = bool(consent)
    stmt = insert(ShopperSession).values(**values).on_duplicate_key_update(**update)
    await db.execute(stmt)


async def _resolve_customer(db: AsyncSession, tenant_id: str, session_id: str | None) -> str | None:
    if not session_id:
        return None
    return (await db.execute(
        select(IdentityLink.customer_ref).where(IdentityLink.tenant_id == tenant_id,
                                                IdentityLink.session_id == session_id)
        .order_by(IdentityLink.linked_at.desc()).limit(1)
    )).scalar_one_or_none()


async def _attribute_search(db: AsyncSession, tenant: Tenant, session_id: str | None, customer_ref: str | None,
                            ts: datetime) -> str | None:
    """Last-touch: oyna ichidagi oxirgi qidiruv (sessiya yoki xaridor bo'yicha)."""
    window = timedelta(days=int(tenant.setting("attribution_days") or 7))
    stmt = tq(VisualSearch, tenant.id, VisualSearch.id).where(
        VisualSearch.created_at >= ts - window, VisualSearch.created_at <= ts + timedelta(minutes=1))
    if session_id and customer_ref:
        stmt = stmt.where((VisualSearch.session_id == session_id) | (VisualSearch.customer_ref == customer_ref))
    elif session_id:
        stmt = stmt.where(VisualSearch.session_id == session_id)
    elif customer_ref:
        stmt = stmt.where(VisualSearch.customer_ref == customer_ref)
    else:
        return None
    return (await db.execute(stmt.order_by(VisualSearch.created_at.desc()).limit(1))).scalar_one_or_none()


async def _open_cart(db: AsyncSession, tenant_id: str, session_id: str | None, customer_ref: str | None) -> CartSession | None:
    if not session_id and not customer_ref:
        return None
    stmt = tq(CartSession, tenant_id).where(CartSession.state == "open")
    stmt = stmt.where(CartSession.session_id == session_id) if session_id else stmt.where(CartSession.customer_ref == customer_ref)
    return (await db.execute(stmt.order_by(CartSession.last_activity_at.desc()).limit(1))).scalar_one_or_none()


def _recalc(cart: CartSession) -> None:
    flag_modified(cart, "items")
    cart.total_minor = sum(int(i.get("price_minor") or 0) * int(i.get("qty") or 1) for i in cart.items)


async def _product_price(db: AsyncSession, tenant_id: str, external_id: str | None) -> tuple[int | None, str | None, str | None]:
    if not external_id:
        return None, None, None
    row = (await db.execute(tq(CatalogProduct, tenant_id, CatalogProduct.price_minor, CatalogProduct.currency,
                                CatalogProduct.name).where(CatalogProduct.external_id == external_id).limit(1))).first()
    return (row[0], row[1], row[2]) if row else (None, None, None)


async def ingest(db: AsyncSession, tenant: Tenant, ev: EventIn, source: str) -> dict[str, int]:
    """Bitta kirish hodisasini qayta ishlaydi. Qaytaradi: {accepted, duplicates}."""
    tenant_id = tenant.id
    ts = _clamp_ts(ev.ts)
    customer_ref = validate_customer_ref(ev.customer_ref) if ev.customer_ref else None
    customer_ref = customer_ref or await _resolve_customer(db, tenant_id, ev.session_id)
    search_id = str(ev.search_id) if ev.search_id else None
    if not search_id and ev.type in ("ADD_TO_CART", "PURCHASE", "PRODUCT_CLICK"):
        search_id = await _attribute_search(db, tenant, ev.session_id, customer_ref, ts)

    # PURCHASE bir nechta mahsulot bilan → har mahsulot alohida qator, event_id deterministik
    lines: list[tuple[str, str | None, int, int | None]] = []
    if ev.items:
        for i, item in enumerate(ev.items):
            eid = str(uuid.uuid5(ev.event_id, f"{i}:{item.id}"))
            lines.append((eid, item.id, item.qty, item.price_minor))
    else:
        lines.append((str(ev.event_id), ev.product_id, ev.qty, ev.price_minor))

    accepted = duplicates = 0
    for eid, product_id, qty, price_minor in lines:
        currency = ev.currency
        name = None
        if price_minor is None or currency is None:
            p_price, p_cur, name = await _product_price(db, tenant_id, product_id)
            price_minor = price_minor if price_minor is not None else p_price
            currency = currency or p_cur or tenant.setting("currency")

        if ev.type == "PURCHASE" and ev.order_ref:
            # Webhook va "rahmat" sahifasi ikkalasi kelsa — order_ref bo'yicha birlashtiriladi
            exists = (await db.execute(tq(Event, tenant_id, Event.id).where(
                Event.type == "PURCHASE", Event.order_ref == ev.order_ref,
                Event.product_external_id == product_id).limit(1))).first()
            if exists:
                duplicates += 1
                continue

        res = await db.execute(insert(Event).prefix_with("IGNORE").values(
            event_id=eid, tenant_id=tenant_id, session_id=ev.session_id, customer_ref=customer_ref,
            search_id=search_id, type=ev.type, product_external_id=product_id, qty=qty,
            price_minor=price_minor, currency=currency, order_ref=ev.order_ref, source=source, ts=ts,
        ))
        if res.rowcount == 0:
            duplicates += 1
            continue
        accepted += 1
        await _side_effects(db, tenant, ev, product_id, qty, price_minor, currency, name, customer_ref, search_id, ts)

    return {"accepted": accepted, "duplicates": duplicates}


async def _side_effects(db: AsyncSession, tenant: Tenant, ev: EventIn, product_id: str | None, qty: int,
                        price_minor: int | None, currency: str | None, name: str | None,
                        customer_ref: str | None, search_id: str | None, ts: datetime) -> None:
    tenant_id = tenant.id
    if ev.type == "PRODUCT_CLICK" and product_id:
        prod = (await db.execute(tq(CatalogProduct, tenant_id).where(
            CatalogProduct.external_id == product_id).limit(1))).scalar_one_or_none()
        if prod:
            prod.popularity = min(1.0, (prod.popularity or 0) + 0.01)

    elif ev.type == "ADD_TO_CART" and product_id:
        cart = await _open_cart(db, tenant_id, ev.session_id, customer_ref)
        if cart is None:
            cart = CartSession(tenant_id=tenant_id, session_id=ev.session_id, customer_ref=customer_ref,
                               search_id=search_id, items=[], currency=currency, last_activity_at=ts)
            db.add(cart)
        items = [dict(i) for i in (cart.items or [])]
        for it in items:
            if it["id"] == product_id:
                it["qty"] = int(it["qty"]) + qty
                break
        else:
            items.append({"id": product_id, "qty": qty, "price_minor": price_minor or 0, "name": name})
        cart.items = items
        cart.search_id = cart.search_id or search_id
        cart.customer_ref = cart.customer_ref or customer_ref
        cart.last_activity_at = ts
        _recalc(cart)

    elif ev.type == "REMOVE_FROM_CART" and product_id:
        cart = await _open_cart(db, tenant_id, ev.session_id, customer_ref)
        if cart:
            items = []
            for it in cart.items or []:
                if it["id"] == product_id:
                    it = {**it, "qty": int(it["qty"]) - qty}
                if int(it["qty"]) > 0:
                    items.append(it)
            cart.items = items
            cart.last_activity_at = ts
            _recalc(cart)

    elif ev.type == "PURCHASE":
        cart = await _open_cart(db, tenant_id, ev.session_id, customer_ref)
        if cart:
            cart.state = "purchased"
            cart.closed_at = ts

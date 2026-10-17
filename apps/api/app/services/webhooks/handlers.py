"""Platforma webhook payloadlarini yagona PURCHASE hodisasiga keltirish."""
import uuid
from typing import Any

from app.core.errors import AppError
from app.services.catalog.normalizer import price_to_minor
from app.services.events.collector import EventIn, EventItem

NAMESPACE = uuid.UUID("6f1c1b0e-6b8a-4c55-9b39-2c0f6e0c7a11")


def _meta(meta: list[dict[str, Any]] | None, key: str) -> str | None:
    for m in meta or []:
        if m.get("key") == key:
            return str(m.get("value"))
    return None


def woocommerce(p: dict[str, Any]) -> tuple[str, EventIn]:
    order_id = str(p.get("id") or p.get("order_id") or "")
    items = [EventItem(id=str(li.get("product_id")), qty=int(li.get("quantity") or 1),
                       price_minor=price_to_minor(li.get("price")), name=li.get("name"))
             for li in p.get("line_items") or []]
    cust = p.get("customer_id")
    return order_id, EventIn(
        event_id=uuid.uuid5(NAMESPACE, f"woo:{order_id}"), type="PURCHASE", order_ref=order_id,
        session_id=_meta(p.get("meta_data"), "_vd_sid") or _meta(p.get("meta_data"), "vd_sid"),
        customer_ref=str(cust) if cust and str(cust) != "0" else None,
        currency=(p.get("currency") or None), items=items or None,
    )


def shopify(p: dict[str, Any]) -> tuple[str, EventIn]:
    order_id = str(p.get("id") or "")
    attrs = {a.get("name"): a.get("value") for a in p.get("note_attributes") or []}
    items = [EventItem(id=str(li.get("product_id")), qty=int(li.get("quantity") or 1),
                       price_minor=price_to_minor(li.get("price")), name=li.get("title"))
             for li in p.get("line_items") or []]
    cust = (p.get("customer") or {}).get("id")
    return order_id, EventIn(
        event_id=uuid.uuid5(NAMESPACE, f"shopify:{order_id}"), type="PURCHASE", order_ref=order_id,
        session_id=attrs.get("vd_sid"), customer_ref=str(cust) if cust else None,
        currency=p.get("currency"), items=items or None,
    )


def opencart(p: dict[str, Any]) -> tuple[str, EventIn]:
    order_id = str(p.get("order_id") or "")
    items = [EventItem(id=str(li.get("product_id")), qty=int(li.get("quantity") or 1),
                       price_minor=price_to_minor(li.get("price")), name=li.get("name"))
             for li in p.get("products") or []]
    cust = p.get("customer_id")
    return order_id, EventIn(
        event_id=uuid.uuid5(NAMESPACE, f"opencart:{order_id}"), type="PURCHASE", order_ref=order_id,
        session_id=p.get("vd_sid"), customer_ref=str(cust) if cust and str(cust) != "0" else None,
        currency=p.get("currency_code"), items=items or None,
    )


def generic(p: dict[str, Any]) -> tuple[str, EventIn]:
    """Umumiy format: {order_ref, session_id?, customer_ref?, currency, items:[{id, qty, price_minor}]}."""
    order_id = str(p.get("order_ref") or p.get("order_id") or "")
    ev = EventIn.model_validate({
        "event_id": p.get("event_id") or str(uuid.uuid5(NAMESPACE, f"generic:{order_id}")),
        "type": "PURCHASE", "order_ref": order_id, "session_id": p.get("session_id"),
        "customer_ref": p.get("customer_ref"), "currency": p.get("currency"), "items": p.get("items"),
    })
    return order_id, ev


HANDLERS = {"woocommerce": woocommerce, "shopify": shopify, "opencart": opencart, "generic": generic}


def parse(platform: str, payload: dict[str, Any]) -> tuple[str, EventIn]:
    handler = HANDLERS.get(platform)
    if not handler:
        raise AppError("UNKNOWN_PLATFORM", f"Platforma qo'llab-quvvatlanmaydi: {platform}", 404)
    order_id, ev = handler(payload)
    if not order_id:
        raise AppError("INVALID_WEBHOOK", "Buyurtma ID topilmadi", 422)
    return order_id, ev

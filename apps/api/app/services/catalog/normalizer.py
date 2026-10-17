"""Har xil manba → yagona Product formati.

Product { external_id, name, description?, category, color?, attributes{},
          price_minor, currency, image_url, product_url, in_stock }
"""
import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.services.matching.normalizer import extract_attributes, normalize_category, normalize_color


class ProductIn(BaseModel):
    external_id: str = Field(min_length=1, max_length=191)
    name: str = Field(min_length=1, max_length=500)
    description: str | None = None
    category: str | None = None
    color: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    price_minor: int | None = Field(default=None, ge=0)
    compare_at_minor: int | None = Field(default=None, ge=0)
    stock_qty: int | None = Field(default=None, ge=0)
    brand: str | None = Field(default=None, max_length=100)
    images: list[str] = Field(default_factory=list, max_length=12)
    currency: str | None = Field(default="UZS", min_length=3, max_length=3)
    image_url: str | None = None
    product_url: str = Field(min_length=1, max_length=1000)
    in_stock: bool = True

    @field_validator("external_id", mode="before")
    @classmethod
    def _ext(cls, v):
        return str(v).strip()

    @field_validator("currency", mode="before")
    @classmethod
    def _cur(cls, v):
        return str(v).upper() if v else "UZS"


def _to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "ha", "in stock", "in_stock", "instock", "mavjud"}


def price_to_minor(value: Any) -> int | None:
    """'129000', '129 000.50 UZS' → 12900000 (tiyin). Hech qachon float emas."""
    if value is None or value == "":
        return None
    s = "".join(ch for ch in str(value) if ch.isdigit() or ch in ".,")
    seps = [ch for ch in s if ch in ".,"]
    if seps:
        last = seps[-1]
        if len(seps) > 1 and all(ch == last for ch in seps):
            s = s.replace(last, "")                      # 1.234.567 → minglik ajratgichlar
        else:
            head, _, tail = s.rpartition(last)          # oxirgisi — o'nlik ajratgich
            s = head.replace(".", "").replace(",", "") + "." + tail
    try:
        return int((Decimal(s) * 100).quantize(Decimal("1")))
    except InvalidOperation:
        return None


def from_raw(raw: dict[str, Any]) -> ProductIn:
    """Feed/CSV/Google Merchant maydon nomlarini moslashtiradi."""
    g = lambda *keys: next((raw[k] for k in keys if k in raw and raw[k] not in (None, "")), None)  # noqa: E731
    price_minor = g("price_minor")
    if price_minor is None:
        price_minor = price_to_minor(g("price", "g:price", "sale_price"))
    availability = g("in_stock", "availability", "g:availability", "stock_status")
    return ProductIn(
        external_id=str(g("external_id", "id", "g:id", "sku", "product_id") or ""),
        name=str(g("name", "title", "g:title") or ""),
        description=g("description", "g:description"),
        category=g("category", "product_type", "g:product_type", "google_product_category"),
        color=g("color", "g:color", "colour"),
        attributes=raw.get("attributes") if isinstance(raw.get("attributes"), dict) else {},
        price_minor=int(price_minor) if price_minor is not None else None,
        compare_at_minor=(int(raw["compare_at_minor"]) if raw.get("compare_at_minor") not in (None, "")
                          else price_to_minor(g("compare_at_price", "old_price", "regular_price"))),
        stock_qty=int(raw["stock_qty"]) if str(raw.get("stock_qty", "")).isdigit() else None,
        brand=g("brand", "g:brand"),
        images=[str(i) for i in raw.get("images", [])] if isinstance(raw.get("images"), list) else [],
        currency=g("currency") or "UZS",
        image_url=g("image_url", "image", "image_link", "g:image_link"),
        product_url=str(g("product_url", "url", "link", "g:link") or ""),
        in_stock=True if availability is None else _to_bool(availability),
    )


def enrich(p: ProductIn) -> dict[str, Any]:
    """Kategoriya/rang/turni normalizatsiya qiladi va content_hash hisoblaydi."""
    text_attrs = extract_attributes(f"{p.name} {p.category or ''} {p.description or ''}")
    category = normalize_category(p.category) if p.category else None
    if not category or category == "boshqa":
        category = text_attrs.get("category") or "boshqa"
    color = normalize_color(p.color) if p.color else text_attrs.get("color")
    attributes = dict(p.attributes)
    if "type" not in attributes and text_attrs.get("type"):
        attributes["type"] = text_attrs["type"]
    data = {
        "external_id": p.external_id, "name": p.name, "description": p.description,
        "category": category, "color": color, "attributes": attributes,
        "price_minor": p.price_minor, "currency": p.currency,
        "compare_at_minor": p.compare_at_minor if p.compare_at_minor and p.price_minor and p.compare_at_minor > p.price_minor else None,
        "stock_qty": p.stock_qty, "brand": p.brand, "images": p.images or None, "image_url": p.image_url,
        "product_url": p.product_url,
        "in_stock": p.in_stock and (p.stock_qty is None or p.stock_qty > 0),
    }
    data["content_hash"] = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()
    return data


def embedding_text(d: dict[str, Any]) -> str:
    attrs = d.get("attributes") or {}
    return " ".join(str(x) for x in [d.get("name"), d.get("category"), d.get("color"), attrs.get("type"),
                                     (d.get("description") or "")[:200]] if x)

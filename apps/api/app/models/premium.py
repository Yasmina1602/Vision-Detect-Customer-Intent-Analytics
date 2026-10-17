"""Faqat PREMIUM (Storefront) jadvallari — savdo do'koni.

Analitika jadvallaridan (events, visual_searches, cart_sessions) alohida: do'kon o'z savati, buyurtmalari va
to'lovlarini shu yerda saqlaydi, analitikaga esa boshqa saytlar kabi oddiy hodisa (source='storefront') yuboradi.
"""
from datetime import datetime

from sqlalchemy import (JSON, BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String,
                        Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col, utcnow, uuid_pk

ORDER_STATUSES = ("new", "confirmed", "shipped", "delivered", "cancelled")
PAYMENT_STATUSES = ("pending", "paid", "failed", "refunded", "cancelled")


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_customers_tenant_email"),)

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(500))
    marketing_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created_at_col()

    @property
    def customer_ref(self) -> str:
        """Analitikaga uzatiladigan neytral ID (e-mail/telefon emas)."""
        return "c_" + self.id.replace("-", "")[:12]


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    customer_id: Mapped[str | None] = mapped_column(String(36))
    session_id: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (CheckConstraint("qty > 0", name="qty_positive"),)

    cart_id: Mapped[str] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True)
    product_id: Mapped[str] = mapped_column(String(36), primary_key=True)   # catalog_products.id
    qty: Mapped[int] = mapped_column(Integer)
    price_minor: Mapped[int] = mapped_column(BigInteger)                     # qo'shilgan paytdagi narx (ma'lumot uchun)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("tenant_id", "number", name="uq_orders_tenant_number"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_orders_tenant_idem"),
        Index("ix_orders_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    customer_id: Mapped[str | None] = mapped_column(String(36))
    number: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="new")
    payment_status: Mapped[str] = mapped_column(String(16), default="pending")
    payment_method: Mapped[str] = mapped_column(String(16), default="cash")      # cash|card|payme|click
    delivery_method: Mapped[str] = mapped_column(String(16), default="courier")  # courier|pickup
    customer_name: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(500))
    note: Mapped[str | None] = mapped_column(String(1000))
    subtotal_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    discount_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    delivery_fee_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    total_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    search_id: Mapped[str | None] = mapped_column(String(36))
    session_id: Mapped[str | None] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class OrderItem(Base):
    __tablename__ = "order_items"

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True)
    product_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    product_external_id: Mapped[str | None] = mapped_column(String(191))
    name: Mapped[str] = mapped_column(String(500))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    qty: Mapped[int] = mapped_column(Integer)
    price_minor: Mapped[int] = mapped_column(BigInteger)


class Payment(Base):
    """To'lov tranzaksiyalari. Callback'lar idempotent: bir xil external_id ikki marta o'tkazilmaydi."""
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_payments_provider_external"),
        CheckConstraint("status IN ('pending','paid','failed','refunded','cancelled')", name="status"),
    )

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(16))          # cash | card | payme | click
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    external_id: Mapped[str | None] = mapped_column(String(128))
    card_mask: Mapped[str | None] = mapped_column(String(32))  # 8600 **** **** 1234 (to'liq raqam saqlanmaydi)
    error: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

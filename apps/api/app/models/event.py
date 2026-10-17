from datetime import datetime

from sqlalchemy import JSON, BigInteger, CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow, uuid_pk

EVENT_TYPES = ("SEARCH", "RESULT_VIEW", "PRODUCT_CLICK", "ADD_TO_CART", "REMOVE_FROM_CART", "PURCHASE")
EVENT_SOURCES = ("widget", "webhook", "server", "storefront")


class Event(Base):
    """Hodisalar. event_id — idempotentlik kaliti (takror yuborilsa ikki marta sanalmaydi).

    PostgreSQL'da oylik partitsiya; MySQL'da (tenant_id, ts) indeksi + retention job.
    """
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "event_id", name="uq_events_tenant_event"),
        Index("ix_events_tenant_ts", "tenant_id", "ts"),
        Index("ix_events_tenant_search_type", "tenant_id", "search_id", "type"),
        Index("ix_events_tenant_order", "tenant_id", "order_ref"),
        CheckConstraint(
            "type IN ('SEARCH','RESULT_VIEW','PRODUCT_CLICK','ADD_TO_CART','REMOVE_FROM_CART','PURCHASE')",
            name="type"),
        CheckConstraint("source IN ('widget','webhook','server','storefront')", name="source"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36))
    tenant_id: Mapped[str] = mapped_column(String(36))
    session_id: Mapped[str | None] = mapped_column(String(64))
    customer_ref: Mapped[str | None] = mapped_column(String(128))
    search_id: Mapped[str | None] = mapped_column(String(36))
    type: Mapped[str] = mapped_column(String(20))
    product_external_id: Mapped[str | None] = mapped_column(String(191))
    qty: Mapped[int] = mapped_column(Integer, default=1)
    price_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str | None] = mapped_column(String(3))
    order_ref: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(String(16))
    ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CartSession(Base):
    """Tashlab ketilgan savat hisobi uchun."""
    __tablename__ = "cart_sessions"
    __table_args__ = (
        Index("ix_cart_sessions_tenant_state", "tenant_id", "state", "last_activity_at"),
        Index("ix_cart_sessions_tenant_session", "tenant_id", "session_id", "state"),
        CheckConstraint("state IN ('open','purchased','abandoned')", name="state"),
    )

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(String(36))
    session_id: Mapped[str | None] = mapped_column(String(64))
    customer_ref: Mapped[str | None] = mapped_column(String(128))
    search_id: Mapped[str | None] = mapped_column(String(36))
    items: Mapped[list] = mapped_column(JSON, default=list)   # [{id, qty, price_minor, name}]
    total_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    currency: Mapped[str | None] = mapped_column(String(3))
    state: Mapped[str] = mapped_column(String(16), default="open")
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

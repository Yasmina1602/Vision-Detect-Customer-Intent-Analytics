"""Auditoriya va target marketing (PII'siz).

customer_profiles — har bir xaridor (customer_ref) yoki anonim sessiya uchun qiziqishlar profili.
campaigns — segmentga yuboriladigan kampaniya (sotuvchi webhook'i, eksport yoki saytdagi blok orqali).
"""
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col, utcnow, uuid_pk


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"
    __table_args__ = (Index("ix_customer_profiles_tenant_seen", "tenant_id", "last_seen"),
                      Index("ix_customer_profiles_tenant_ref", "tenant_id", "customer_ref"))

    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_key: Mapped[str] = mapped_column(String(140), primary_key=True)   # customer_ref yoki "s:<vd_sid>"
    customer_ref: Mapped[str | None] = mapped_column(String(128))
    session_id: Mapped[str | None] = mapped_column(String(64))
    interests: Mapped[dict] = mapped_column(JSON, default=dict)   # {"category": {...}, "color": {...}, "type": {...}}
    segments: Mapped[list] = mapped_column(JSON, default=list)    # ["interest:poyabzal", "abandoned_cart", ...]
    unmet: Mapped[list] = mapped_column(JSON, default=list)       # qidirgan, lekin topmagan demand_key'lar
    searches: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    carts: Mapped[int] = mapped_column(Integer, default=0)
    purchases: Mapped[int] = mapped_column(Integer, default=0)
    revenue_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    abandoned_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(200))
    segment: Mapped[str] = mapped_column(String(191))              # masalan "interest:poyabzal"
    channel: Mapped[str] = mapped_column(String(16), default="webhook")   # webhook | onsite | export
    title: Mapped[str | None] = mapped_column(String(200))
    message: Mapped[str | None] = mapped_column(Text)
    discount_code: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(16), default="draft")      # draft | active | sent | stopped
    audience_size: Mapped[int] = mapped_column(Integer, default=0)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)               # {"sent", "impressions", "clicks", "error"}
    created_by: Mapped[str | None] = mapped_column(String(36))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = created_at_col()

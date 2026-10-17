from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow, uuid_pk


class ShopperSession(Base):
    """Anonim first-party sessiya (vd_sid)."""
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    device: Mapped[str | None] = mapped_column(String(16))
    country: Mapped[str | None] = mapped_column(String(2))


class IdentityLink(Base):
    """vd_sid ↔ sotuvchining ichki xaridor ID'si (username/email EMAS)."""
    __tablename__ = "identity_links"

    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_ref: Mapped[str] = mapped_column(String(128), primary_key=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class VisualSearch(Base):
    __tablename__ = "visual_searches"
    __table_args__ = (
        Index("ix_visual_searches_tenant_created", "tenant_id", "created_at"),
        Index("ix_visual_searches_tenant_demand", "tenant_id", "is_unmet_demand", "demand_key"),
    )

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(String(36))
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    customer_ref: Mapped[str | None] = mapped_column(String(128))
    image_hash: Mapped[str] = mapped_column(String(64))       # sha256; asl rasm SAQLANMAYDI
    prompt_version: Mapped[str] = mapped_column(String(16))
    ai_detected: Mapped[dict] = mapped_column(JSON)
    model_used: Mapped[str | None] = mapped_column(String(100))
    best_score: Mapped[float | None] = mapped_column(Float)
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    is_unmet_demand: Mapped[bool] = mapped_column(Boolean, default=False)
    demand_key: Mapped[str | None] = mapped_column(String(191))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

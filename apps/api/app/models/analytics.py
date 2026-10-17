from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class UnmetDemandCluster(Base):
    __tablename__ = "unmet_demand_clusters"

    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    demand_key: Mapped[str] = mapped_column(String(191), primary_key=True)
    sample_query: Mapped[str | None] = mapped_column(String(500))
    search_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_sessions: Mapped[int] = mapped_column(Integer, default=0)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime)
    ai_suggestion: Mapped[str | None] = mapped_column(Text)


class DailyStat(Base):
    __tablename__ = "daily_stats"

    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    metrics: Mapped[dict] = mapped_column(JSON)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (UniqueConstraint("tenant_id", "source", "external_id", name="uq_webhook_deliveries_dedupe"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(36))
    source: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="received")  # received|processed|failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

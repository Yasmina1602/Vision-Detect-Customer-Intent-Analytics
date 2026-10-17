from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow, uuid_pk


class CatalogProduct(Base):
    """Barcha rejimlar (feed/proxy/hosted) yagona Product formatiga keltiriladi."""
    __tablename__ = "catalog_products"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id", name="uq_catalog_products_tenant_external"),
        Index("ix_catalog_products_tenant_category", "tenant_id", "category", "in_stock", "is_deleted"),
    )

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    external_id: Mapped[str] = mapped_column(String(191))
    name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    color: Mapped[str | None] = mapped_column(String(50))
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    price_minor: Mapped[int | None] = mapped_column(BigInteger)
    compare_at_minor: Mapped[int | None] = mapped_column(BigInteger)  # chegirmadan oldingi narx (aksiya)
    currency: Mapped[str | None] = mapped_column(String(3))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    images: Mapped[list | None] = mapped_column(JSON)               # qo'shimcha rasmlar (galereya)
    brand: Mapped[str | None] = mapped_column(String(100))
    sales_count: Mapped[int] = mapped_column(Integer, default=0)
    product_url: Mapped[str] = mapped_column(String(1000))
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    stock_qty: Mapped[int | None] = mapped_column(Integer)          # faqat hosted (Premium)
    embedding: Mapped[list | None] = mapped_column(JSON)            # pgvector o'rniga JSON
    content_hash: Mapped[str | None] = mapped_column(String(64))
    popularity: Mapped[float] = mapped_column(Float, default=0.0)   # 0..1, kliklar asosida
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class CatalogSyncRun(Base):
    __tablename__ = "catalog_sync_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    source: Mapped[str] = mapped_column(String(32), default="feed")   # feed | push | csv | manual
    status: Mapped[str] = mapped_column(String(16))                   # running | success | failed
    items_seen: Mapped[int] = mapped_column(Integer, default=0)
    items_changed: Mapped[int] = mapped_column(Integer, default=0)
    items_deleted: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

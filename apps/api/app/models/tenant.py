from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, LargeBinary, String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col, utcnow, uuid_pk

DEFAULT_TENANT_SETTINGS = {
    "unmet_threshold": 0.45,
    "language": "uz",
    "theme": {"primary": "#6d28d9", "position": "bottom-right"},
    "search_selector": "",
    "consent_mode": "implied",       # implied | explicit
    "attribution_days": 7,
    "abandon_after_hours": 24,
    "currency": "UZS",
    "timezone": "Asia/Tashkent",
    "customer_deeplink": "",          # https://shop.uz/admin/customers/{customer_ref}
    "cart_adapter": "none",           # none | woocommerce | shopify | opencart | custom
    "thank_you_url_pattern": "",
    "feed_url": "",
    "feed_format": "json",            # json | csv
    "daily_search_quota": 2000,
}


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint("plan IN ('basic','premium')", name="plan"),
        CheckConstraint("status IN ('trial','active','suspended','deleted')", name="status"),
        CheckConstraint("catalog_mode IN ('feed','proxy','hosted')", name="catalog_mode"),
    )

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    plan: Mapped[str] = mapped_column(String(16), default="basic")
    status: Mapped[str] = mapped_column(String(16), default="active")
    catalog_mode: Mapped[str] = mapped_column(String(16), default="feed")
    platform: Mapped[str | None] = mapped_column(String(32))
    settings: Mapped[dict] = mapped_column(JSON, default=lambda: dict(DEFAULT_TENANT_SETTINGS))
    data_region: Mapped[str] = mapped_column(String(16), default="eu")
    created_at: Mapped[datetime] = created_at_col()

    def setting(self, key: str):
        return (self.settings or {}).get(key, DEFAULT_TENANT_SETTINGS.get(key))


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    public_key: Mapped[str] = mapped_column(String(64), unique=True)
    secret_key_hash: Mapped[str] = mapped_column(String(128), index=True)
    secret_key_hint: Mapped[str] = mapped_column(String(16))           # sk_live_…ab12
    webhook_secret_enc: Mapped[bytes] = mapped_column(LargeBinary)
    allowed_origins: Mapped[list] = mapped_column(JSON, default=list)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = created_at_col()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str | None] = mapped_column(String(36), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str | None] = mapped_column(String(255))
    meta: Mapped[dict | None] = mapped_column(JSON)
    ip: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class AiModel(Base):
    """Gemini model nomlari kodga yozilmaydi — shu jadvalda boshqariladi."""
    __tablename__ = "ai_models"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    priority: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(Text)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)

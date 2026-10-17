from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col, uuid_pk

TENANT_ROLES = ("owner", "admin", "catalog_manager", "analyst", "viewer")
ROLE_RANK = {r: i for i, r in enumerate(reversed(TENANT_ROLES))}  # viewer=0 … owner=4


class User(Base):
    """Platforma foydalanuvchilari (dashboard). Do'kon xaridorlari bilan aralashtirilmaydi."""
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("platform_role IN ('super_admin','support','user')", name="platform_role"),)

    id: Mapped[str] = uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True)   # har doim lower()
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(200))
    platform_role: Mapped[str] = mapped_column(String(16), default="user")
    totp_secret_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_logins: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = created_at_col()


class TenantMembership(Base):
    __tablename__ = "tenant_memberships"
    __table_args__ = (
        CheckConstraint("role IN ('owner','admin','catalog_manager','analyst','viewer')", name="role"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = created_at_col()

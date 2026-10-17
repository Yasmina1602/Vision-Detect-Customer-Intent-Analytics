"""Bog'liqliklar: DB, JWT foydalanuvchi, tenant konteksti, rollar, public/secret kalitlar."""
from dataclasses import dataclass
from urllib.parse import urlparse

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, Forbidden, Unauthorized
from app.core.security import decode_token, hash_key
from app.db.base import utcnow
from app.db.session import get_db
from app.models import ApiKey, AuditLog, Tenant, TenantMembership, User
from app.models.user import ROLE_RANK

__all__ = ["get_db", "current_user", "TenantCtx", "tenant_ctx", "require_role", "require_super_admin",
           "public_tenant", "server_tenant", "audit", "client_ip"]


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")
    return ip


def masked_ip(ip: str) -> str:
    """IP anonimlashtirish: oxirgi oktet maskalanadi."""
    if "." in ip:
        return ".".join(ip.split(".")[:3] + ["0"])
    if ":" in ip:
        return ":".join(ip.split(":")[:4]) + "::"
    return ip


async def current_user(authorization: str | None = Header(default=None),
                       db: AsyncSession = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized()
    data = decode_token(authorization[7:], "access")
    if not data:
        raise Unauthorized("Sessiya muddati tugagan")
    user = await db.get(User, data["sub"])
    if not user or not user.is_active:
        raise Unauthorized("Foydalanuvchi faol emas")
    return user


async def require_super_admin(user: User = Depends(current_user)) -> User:
    if user.platform_role != "super_admin":
        raise Forbidden("Faqat platforma administratori uchun")
    return user


@dataclass
class TenantCtx:
    tenant: Tenant
    user: User
    role: str

    @property
    def id(self) -> str:
        return self.tenant.id

    def can(self, min_role: str) -> bool:
        return ROLE_RANK[self.role] >= ROLE_RANK[min_role]


async def tenant_ctx(x_tenant_id: str | None = Header(default=None),
                     user: User = Depends(current_user),
                     db: AsyncSession = Depends(get_db)) -> TenantCtx:
    stmt = select(TenantMembership).where(TenantMembership.user_id == user.id)
    if x_tenant_id:
        stmt = stmt.where(TenantMembership.tenant_id == x_tenant_id)
    membership = (await db.execute(stmt.limit(1))).scalar_one_or_none()

    if membership:
        tenant = await db.get(Tenant, membership.tenant_id)
        role = membership.role
    elif user.platform_role in ("super_admin", "support") and x_tenant_id:
        tenant = await db.get(Tenant, x_tenant_id)
        role = "owner" if user.platform_role == "super_admin" else "viewer"
    else:
        raise Forbidden("Siz bu do'kon a'zosi emassiz")
    if not tenant or tenant.status == "deleted":
        raise Forbidden("Do'kon topilmadi")
    return TenantCtx(tenant=tenant, user=user, role=role)


def require_role(min_role: str):
    async def _dep(ctx: TenantCtx = Depends(tenant_ctx)) -> TenantCtx:
        if not ctx.can(min_role):
            raise Forbidden(f"Bu amal uchun kamida '{min_role}' roli kerak")
        return ctx
    return _dep


def require_premium(ctx: TenantCtx) -> None:
    if ctx.tenant.plan != "premium":
        raise AppError("PLAN_REQUIRED", "Bu imkoniyat faqat Premium tarifda mavjud", 402)


async def audit(db: AsyncSession, request: Request | None, action: str, *, tenant_id: str | None = None,
                actor: User | None = None, target: str | None = None, meta: dict | None = None) -> None:
    db.add(AuditLog(tenant_id=tenant_id, actor_user_id=actor.id if actor else None, action=action,
                    target=target, meta=meta, ip=masked_ip(client_ip(request)) if request else None))


# ---------- Vidjet (public key + Origin) ----------
def _origin_allowed(origin: str | None, allowed: list[str]) -> bool:
    if not allowed:
        return True   # allowlist bo'sh — Integrations sahifasida ogohlantirish ko'rsatiladi
    if not origin:
        return False
    host = urlparse(origin).hostname or ""
    if settings.is_dev and host in ("localhost", "127.0.0.1"):
        return True
    for entry in allowed:
        entry = entry.strip().lower()
        e_host = urlparse(entry).hostname if "://" in entry else entry
        if not e_host:
            continue
        if e_host.startswith("*.") and (host == e_host[2:] or host.endswith(e_host[1:])):
            return True
        if host == e_host:
            return True
    return False


async def _tenant_by_public_key(db: AsyncSession, pk: str) -> tuple[Tenant, ApiKey]:
    key = (await db.execute(select(ApiKey).where(ApiKey.public_key == pk, ApiKey.revoked_at.is_(None)))).scalar_one_or_none()
    if not key:
        raise AppError("INVALID_KEY", "API kalit noto'g'ri yoki bekor qilingan", 401)
    tenant = await db.get(Tenant, key.tenant_id)
    if not tenant or tenant.status not in ("active", "trial"):
        raise AppError("TENANT_INACTIVE", "Do'kon faol emas", 403)
    return tenant, key


async def public_tenant(request: Request, x_vision_key: str | None = Header(default=None),
                        db: AsyncSession = Depends(get_db)) -> Tenant:
    pk = x_vision_key or request.query_params.get("key")
    if not pk:
        raise AppError("INVALID_KEY", "Public key talab qilinadi", 401)
    tenant, key = await _tenant_by_public_key(db, pk)
    if not _origin_allowed(request.headers.get("origin"), key.allowed_origins or []):
        raise AppError("ORIGIN_NOT_ALLOWED", "Bu domen kalit uchun ruxsat etilmagan", 403)
    request.state.tenant_id = tenant.id
    return tenant


async def server_tenant(request: Request, authorization: str | None = Header(default=None),
                        db: AsyncSession = Depends(get_db)) -> tuple[Tenant, ApiKey]:
    if not authorization or not authorization.lower().startswith("bearer sk_"):
        raise AppError("INVALID_KEY", "Authorization: Bearer sk_live_... talab qilinadi", 401)
    key = (await db.execute(select(ApiKey).where(ApiKey.secret_key_hash == hash_key(authorization[7:].strip()),
                                                 ApiKey.revoked_at.is_(None)))).scalar_one_or_none()
    if not key:
        raise AppError("INVALID_KEY", "Secret key noto'g'ri yoki bekor qilingan", 401)
    tenant = await db.get(Tenant, key.tenant_id)
    if not tenant or tenant.status not in ("active", "trial"):
        raise AppError("TENANT_INACTIVE", "Do'kon faol emas", 403)
    key.last_used_at = utcnow()
    request.state.tenant_id = tenant.id
    return tenant, key

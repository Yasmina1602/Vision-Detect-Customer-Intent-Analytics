import re
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (encrypt, generate_public_key, generate_secret_key, generate_webhook_secret,
                               hash_key)
from app.db.base import utcnow
from app.models import ApiKey, Tenant
from app.models.tenant import DEFAULT_TENANT_SETTINGS


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower().replace("'", "")).strip("-")
    return s[:60] or "shop"


async def unique_slug(db: AsyncSession, name: str) -> str:
    base = slugify(name)
    slug = base
    while (await db.execute(select(Tenant.id).where(Tenant.slug == slug))).first():
        slug = f"{base}-{secrets.token_hex(2)}"
    return slug


async def issue_api_key(db: AsyncSession, tenant_id: str, allowed_origins: list[str] | None = None) -> tuple[ApiKey, str, str]:
    """Yangi kalitlar to'plami. Qaytaradi: (ApiKey, secret_key, webhook_secret) — sirlar faqat bir marta ko'rsatiladi."""
    secret = generate_secret_key()
    whsec = generate_webhook_secret()
    key = ApiKey(tenant_id=tenant_id, public_key=generate_public_key(), secret_key_hash=hash_key(secret),
                 secret_key_hint=f"sk_live_…{secret[-4:]}", webhook_secret_enc=encrypt(whsec),
                 allowed_origins=allowed_origins or [], created_at=utcnow())
    db.add(key)
    await db.flush()
    return key, secret, whsec


async def create_tenant_with_key(db: AsyncSession, name: str, plan: str = "basic", platform: str | None = None,
                                 catalog_mode: str | None = None) -> tuple[Tenant, tuple[ApiKey, str, str]]:
    tenant = Tenant(name=name, slug=await unique_slug(db, name), plan=plan, platform=platform,
                    catalog_mode=catalog_mode or ("hosted" if plan == "premium" else "feed"),
                    settings=dict(DEFAULT_TENANT_SETTINGS), status="active")
    db.add(tenant)
    await db.flush()
    keys = await issue_api_key(db, tenant.id)
    return tenant, keys

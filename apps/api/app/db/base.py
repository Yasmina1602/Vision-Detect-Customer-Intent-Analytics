"""Deklarativ baza va umumiy tiplar.

MySQL moslashuvi (README PostgreSQL sxemasidan):
  UUID → CHAR(36), JSONB/TEXT[] → JSON, timestamptz → DATETIME(6) (har doim UTC),
  CITEXT → VARCHAR + kichik harfga normalizatsiya, vector → JSON (embedding),
  RLS → repository qatlamidagi majburiy tenant filtri (app/db/repositories).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData, String
from sqlalchemy.orm import DeclarativeBase, mapped_column

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


def utcnow() -> datetime:
    """DB'da naive UTC saqlanadi (MySQL DATETIME zona saqlamaydi)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_uuid() -> str:
    return str(uuid.uuid4())


def uuid_pk():
    return mapped_column(String(36), primary_key=True, default=new_uuid)


def created_at_col():
    return mapped_column(DateTime, nullable=False, default=utcnow)

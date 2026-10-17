"""Boshlang'ich sxema (v2).

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-16

Jadvallar modellar snapshotidan yaratiladi. Agar bazada shu nomdagi, lekin boshqa tuzilmadagi
jadval bo'lsa (masalan eski v1 loyihadan), migratsiya hech narsani o'zgartirmasdan to'xtaydi.
"""
import sqlalchemy as sa
from alembic import op

from app.db.base import Base
import app.models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = set(insp.get_table_names())
    conflicts = []
    for name, table in Base.metadata.tables.items():
        if name in existing:
            cols = {c["name"] for c in insp.get_columns(name)}
            if not {c.name for c in table.columns} <= cols:
                conflicts.append(name)
    if conflicts:
        raise RuntimeError(
            "Bazada boshqa tuzilmadagi jadvallar bor: " + ", ".join(sorted(conflicts)) +
            ". Ularni qayta nomlang (masalan legacy_v1_*) yoki yangi baza ishlating. "
            "Batafsil: apps/api/README.md → 'Eski jadvallar'.")
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())

"""Storefront (buyurtma, to'lov), aksiya narxlari, auditoriya profillari va kampaniyalar.

Revision ID: 0002_storefront_marketing
Revises: 0001_initial
Create Date: 2026-10-17

Idempotent: 0001 joriy modellar snapshotidan yaratilgani uchun yangi bazada ustunlar allaqachon bo'lishi mumkin.
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_storefront_marketing"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

NEW_COLUMNS = {
    "catalog_products": [
        sa.Column("compare_at_minor", sa.BigInteger, nullable=True),
        sa.Column("images", sa.JSON, nullable=True),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("sales_count", sa.Integer, nullable=False, server_default="0"),
    ],
    "customers": [
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("marketing_consent", sa.Boolean, nullable=False, server_default=sa.false()),
    ],
    "orders": [
        sa.Column("payment_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("payment_method", sa.String(16), nullable=False, server_default="cash"),
        sa.Column("delivery_method", sa.String(16), nullable=False, server_default="courier"),
        sa.Column("customer_name", sa.String(200), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("subtotal_minor", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("discount_minor", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("delivery_fee_minor", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(64), nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    ],
    "order_items": [
        sa.Column("product_external_id", sa.String(191), nullable=True),
        sa.Column("image_url", sa.String(1000), nullable=True),
    ],
}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    for table, cols in NEW_COLUMNS.items():
        existing = {c["name"] for c in insp.get_columns(table)}
        for col in cols:
            if col.name not in existing:
                op.add_column(table, col)

    order_uniques = {u["name"] for u in insp.get_unique_constraints("orders")}
    if "uq_orders_tenant_number" not in order_uniques:
        op.create_unique_constraint("uq_orders_tenant_number", "orders", ["tenant_id", "number"])
    if "uq_orders_tenant_idem" not in order_uniques:
        op.create_unique_constraint("uq_orders_tenant_idem", "orders", ["tenant_id", "idempotency_key"])
    if "ix_orders_tenant_created" not in {i["name"] for i in insp.get_indexes("orders")}:
        op.create_index("ix_orders_tenant_created", "orders", ["tenant_id", "created_at"])

    if "payments" not in tables:
        op.create_table(
            "payments",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
            sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("provider", sa.String(16), nullable=False),
            sa.Column("amount_minor", sa.BigInteger, nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("external_id", sa.String(128)),
            sa.Column("card_mask", sa.String(32)),
            sa.Column("error", sa.Text),
            sa.Column("raw", sa.JSON),
            sa.Column("created_at", sa.DateTime, nullable=False),
            sa.Column("updated_at", sa.DateTime),
            sa.UniqueConstraint("provider", "external_id", name="uq_payments_provider_external"),
            sa.CheckConstraint("status IN ('pending','paid','failed','refunded','cancelled')", name="ck_payments_status"),
        )

    if "customer_profiles" not in tables:
        op.create_table(
            "customer_profiles",
            sa.Column("tenant_id", sa.String(36), primary_key=True),
            sa.Column("profile_key", sa.String(140), primary_key=True),
            sa.Column("customer_ref", sa.String(128)),
            sa.Column("session_id", sa.String(64)),
            sa.Column("interests", sa.JSON),
            sa.Column("segments", sa.JSON),
            sa.Column("unmet", sa.JSON),
            sa.Column("searches", sa.Integer, nullable=False, server_default="0"),
            sa.Column("clicks", sa.Integer, nullable=False, server_default="0"),
            sa.Column("carts", sa.Integer, nullable=False, server_default="0"),
            sa.Column("purchases", sa.Integer, nullable=False, server_default="0"),
            sa.Column("revenue_minor", sa.BigInteger, nullable=False, server_default="0"),
            sa.Column("abandoned_minor", sa.BigInteger, nullable=False, server_default="0"),
            sa.Column("last_seen", sa.DateTime),
            sa.Column("updated_at", sa.DateTime, nullable=False),
        )
        op.create_index("ix_customer_profiles_tenant_seen", "customer_profiles", ["tenant_id", "last_seen"])
        op.create_index("ix_customer_profiles_tenant_ref", "customer_profiles", ["tenant_id", "customer_ref"])

    if "campaigns" not in tables:
        op.create_table(
            "campaigns",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("segment", sa.String(191), nullable=False),
            sa.Column("channel", sa.String(16), nullable=False),
            sa.Column("title", sa.String(200)),
            sa.Column("message", sa.Text),
            sa.Column("discount_code", sa.String(50)),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("audience_size", sa.Integer, nullable=False, server_default="0"),
            sa.Column("stats", sa.JSON),
            sa.Column("created_by", sa.String(36)),
            sa.Column("sent_at", sa.DateTime),
            sa.Column("created_at", sa.DateTime, nullable=False),
        )


def downgrade() -> None:
    op.drop_table("campaigns")
    op.drop_table("customer_profiles")
    op.drop_table("payments")
    for table, cols in NEW_COLUMNS.items():
        for col in cols:
            op.drop_column(table, col.name)

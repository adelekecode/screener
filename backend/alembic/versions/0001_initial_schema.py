"""Initial scanner schema.

Revision ID: 0001
Revises:
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("discovered_count", sa.Integer(), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("qualified_count", sa.Integer(), nullable=False),
        sa.Column("alerted_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_scans_status", "scans", ["status"])

    op.create_table(
        "opportunities",
        sa.Column("pair_address", sa.String(64), primary_key=True),
        sa.Column("token_address", sa.String(64), nullable=False),
        sa.Column("chain_id", sa.String(32), nullable=False),
        sa.Column("dex_id", sa.String(64)),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("price_usd", sa.Float()),
        sa.Column("market_cap_usd", sa.Float()),
        sa.Column("liquidity_usd", sa.Float()),
        sa.Column("volume_5m_usd", sa.Float()),
        sa.Column("volume_1h_usd", sa.Float()),
        sa.Column("volume_10m_usd", sa.Float()),
        sa.Column("buys_5m", sa.Integer()),
        sa.Column("sells_5m", sa.Integer()),
        sa.Column("buys_10m", sa.Integer()),
        sa.Column("sells_10m", sa.Integer()),
        sa.Column("unique_buyers_10m", sa.Integer()),
        sa.Column("pair_created_at", sa.DateTime(timezone=True)),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("qualified", sa.Boolean(), nullable=False),
        sa.Column("rejection_reasons", postgresql.JSONB(), nullable=False),
        sa.Column("risk_flags", postgresql.JSONB(), nullable=False),
        sa.Column("checks", postgresql.JSONB(), nullable=False),
        sa.Column("score_breakdown", postgresql.JSONB(), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_opportunities_token_address", "opportunities", ["token_address"])
    op.create_index("ix_opportunities_score", "opportunities", ["score"])
    op.create_index("ix_opportunities_qualified", "opportunities", ["qualified"])
    op.create_index("ix_opportunities_last_seen_at", "opportunities", ["last_seen_at"])

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pair_address",
            sa.String(64),
            sa.ForeignKey("opportunities.pair_address"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.Integer()),
        sa.Column("error", sa.Text()),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("initial_price_usd", sa.Float()),
        sa.Column("current_price_usd", sa.Float()),
        sa.Column("maximum_price_usd", sa.Float()),
        sa.Column("minimum_price_usd", sa.Float()),
        sa.Column("maximum_gain_percentage", sa.Float()),
        sa.Column("maximum_decline_percentage", sa.Float()),
        sa.Column("last_tracked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_alerts_pair_address", "alerts", ["pair_address"])

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_alerts_pair_address", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_opportunities_last_seen_at", table_name="opportunities")
    op.drop_index("ix_opportunities_qualified", table_name="opportunities")
    op.drop_index("ix_opportunities_score", table_name="opportunities")
    op.drop_index("ix_opportunities_token_address", table_name="opportunities")
    op.drop_table("opportunities")
    op.drop_index("ix_scans_status", table_name="scans")
    op.drop_table("scans")

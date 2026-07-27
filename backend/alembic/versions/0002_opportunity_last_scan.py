"""Link opportunities to the scan that last touched them.

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("last_scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id")),
    )
    op.create_index(
        "ix_opportunities_last_scan_id", "opportunities", ["last_scan_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_opportunities_last_scan_id", table_name="opportunities")
    op.drop_column("opportunities", "last_scan_id")

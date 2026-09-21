"""add dismissed column to papers

Revision ID: 73a881b602b6
Revises: 1e01f8237a75
Create Date: 2026-09-18 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "73a881b602b6"
down_revision = "1e01f8237a75"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("papers", sa.Column("dismissed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("papers", "dismissed", server_default=None)


def downgrade() -> None:
    op.drop_column("papers", "dismissed")

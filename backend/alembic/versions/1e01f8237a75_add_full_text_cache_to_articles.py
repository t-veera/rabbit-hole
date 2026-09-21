"""add full_text cache column to articles

Revision ID: 1e01f8237a75
Revises: 7ebb69bcacf6
Create Date: 2026-09-17 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1e01f8237a75"
down_revision = "7ebb69bcacf6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("full_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("articles", "full_text")

"""add app_settings table

Revision ID: 30cdab634288
Revises: b21f9a4c1d02
Create Date: 2026-09-21 18:33:30.530059

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30cdab634288'
down_revision: Union[str, None] = 'b21f9a4c1d02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("anthropic_api_key", sa.String(), nullable=True),
        sa.Column("unpaywall_email", sa.String(), nullable=True),
        sa.Column("openalex_mailto", sa.String(), nullable=True),
        sa.Column("ncbi_api_key", sa.String(), nullable=True),
        sa.Column("semantic_scholar_api_key", sa.String(), nullable=True),
        sa.Column("core_api_key", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("app_settings")

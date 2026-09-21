"""add merged_openalex_ids to researchers

Revision ID: a66ed702db03
Revises: de72ca7a453c
Create Date: 2026-09-15 19:07:17.337986

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a66ed702db03'
down_revision: Union[str, None] = 'de72ca7a453c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('researchers', sa.Column('merged_openalex_ids', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('researchers', 'merged_openalex_ids')

"""add researcher_id to topics for following people

Revision ID: ae68b0d8d461
Revises: 77fae48a65ff
Create Date: 2026-09-15 16:14:21.208842

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae68b0d8d461'
down_revision: Union[str, None] = '77fae48a65ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('topics', sa.Column('researcher_id', sa.UUID(), nullable=True))
    op.create_foreign_key('topics_researcher_id_fkey', 'topics', 'researchers', ['researcher_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('topics_researcher_id_fkey', 'topics', type_='foreignkey')
    op.drop_column('topics', 'researcher_id')

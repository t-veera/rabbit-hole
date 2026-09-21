"""add pdf upload support: paper origin enum replaces is_from_user_source

Revision ID: de72ca7a453c
Revises: a6593d4dfba5
Create Date: 2026-09-15 16:55:52.668141

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'de72ca7a453c'
down_revision: Union[str, None] = 'a6593d4dfba5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

paper_origin = postgresql.ENUM('source', 'discovered', 'uploaded', name='paper_origin')


def upgrade() -> None:
    paper_origin.create(op.get_bind(), checkfirst=True)
    # Nullable first so the data migration below has something to fill in —
    # can't add a NOT NULL column with no default onto a table with rows.
    op.add_column('papers', sa.Column('origin', paper_origin, nullable=True))
    op.execute(
        "UPDATE papers SET origin = (CASE WHEN is_from_user_source THEN 'source' ELSE 'discovered' END)::paper_origin"
    )
    op.alter_column('papers', 'origin', nullable=False)
    op.drop_column('papers', 'is_from_user_source')


def downgrade() -> None:
    op.add_column('papers', sa.Column('is_from_user_source', sa.Boolean(), nullable=True))
    op.execute("UPDATE papers SET is_from_user_source = (origin = 'source')")
    op.alter_column('papers', 'is_from_user_source', nullable=False)
    op.drop_column('papers', 'origin')
    paper_origin.drop(op.get_bind(), checkfirst=True)

"""cascade topic deletion to dependent rows

Revision ID: 123fb6af24cd
Revises: ae68b0d8d461
Create Date: 2026-09-15 16:17:14.681588

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '123fb6af24cd'
down_revision: Union[str, None] = 'ae68b0d8d461'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Deleting a topic (or unfollowing a person) previously 500'd once any
    # paper/article/book existed under it — no ON DELETE behavior meant
    # Postgres just refused. Papers etc. should survive in the library with
    # topic_id cleared; seen_log rows are meaningless without their topic.
    op.drop_constraint(op.f('articles_topic_id_fkey'), 'articles', type_='foreignkey')
    op.create_foreign_key('articles_topic_id_fkey', 'articles', 'topics', ['topic_id'], ['id'], ondelete='SET NULL')
    op.drop_constraint(op.f('books_topic_id_fkey'), 'books', type_='foreignkey')
    op.create_foreign_key('books_topic_id_fkey', 'books', 'topics', ['topic_id'], ['id'], ondelete='SET NULL')
    op.drop_constraint(op.f('papers_topic_id_fkey'), 'papers', type_='foreignkey')
    op.create_foreign_key('papers_topic_id_fkey', 'papers', 'topics', ['topic_id'], ['id'], ondelete='SET NULL')
    op.drop_constraint(op.f('seen_log_topic_id_fkey'), 'seen_log', type_='foreignkey')
    op.create_foreign_key('seen_log_topic_id_fkey', 'seen_log', 'topics', ['topic_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint('seen_log_topic_id_fkey', 'seen_log', type_='foreignkey')
    op.create_foreign_key(op.f('seen_log_topic_id_fkey'), 'seen_log', 'topics', ['topic_id'], ['id'])
    op.drop_constraint('papers_topic_id_fkey', 'papers', type_='foreignkey')
    op.create_foreign_key(op.f('papers_topic_id_fkey'), 'papers', 'topics', ['topic_id'], ['id'])
    op.drop_constraint('books_topic_id_fkey', 'books', type_='foreignkey')
    op.create_foreign_key(op.f('books_topic_id_fkey'), 'books', 'topics', ['topic_id'], ['id'])
    op.drop_constraint('articles_topic_id_fkey', 'articles', type_='foreignkey')
    op.create_foreign_key(op.f('articles_topic_id_fkey'), 'articles', 'topics', ['topic_id'], ['id'])

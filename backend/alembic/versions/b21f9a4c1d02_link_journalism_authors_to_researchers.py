"""link journalism article authors to researchers

Revision ID: b21f9a4c1d02
Revises: 73a881b602b6
Create Date: 2026-09-19 00:00:00.000000

"""
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "b21f9a4c1d02"
down_revision = "73a881b602b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("author_researcher_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "articles_author_researcher_id_fkey",
        "articles",
        "researchers",
        ["author_researcher_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Backfill: give existing journalism bylines a Researcher row too, so
    # articles ingested before this migration link out the same as new ones
    # — one Researcher per distinct name (case-insensitive), reusing an
    # existing row if a paper author or an earlier byline already used it.
    bind = op.get_bind()
    articles = sa.table(
        "articles",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("author_name", sa.String),
        sa.column("author_researcher_id", UUID(as_uuid=True)),
    )
    researchers = sa.table(
        "researchers",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    rows = bind.execute(
        sa.select(articles.c.id, articles.c.author_name).where(articles.c.author_name.isnot(None))
    ).fetchall()

    researcher_id_by_lower_name: dict[str, uuid.UUID] = {}
    for row in bind.execute(sa.select(researchers.c.id, researchers.c.name)).fetchall():
        researcher_id_by_lower_name.setdefault(row.name.lower(), row.id)

    now = datetime.now(timezone.utc)
    for row in rows:
        key = row.author_name.lower()
        researcher_id = researcher_id_by_lower_name.get(key)
        if researcher_id is None:
            researcher_id = uuid.uuid4()
            bind.execute(researchers.insert().values(id=researcher_id, name=row.author_name, created_at=now))
            researcher_id_by_lower_name[key] = researcher_id
        bind.execute(
            articles.update().where(articles.c.id == row.id).values(author_researcher_id=researcher_id)
        )


def downgrade() -> None:
    op.drop_constraint("articles_author_researcher_id_fkey", "articles", type_="foreignkey")
    op.drop_column("articles", "author_researcher_id")

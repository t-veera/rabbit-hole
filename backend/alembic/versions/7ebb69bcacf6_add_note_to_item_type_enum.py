"""add note to item_type enum

Revision ID: 7ebb69bcacf6
Revises: a66ed702db03
Create Date: 2026-09-17 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "7ebb69bcacf6"
down_revision = "a66ed702db03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE can't run inside the transaction Alembic
    # normally wraps migrations in (Postgres forbids using a new enum value
    # in the same transaction that added it, and older server versions
    # reject the ADD VALUE itself in a transaction block) — autocommit_block
    # runs this one statement outside that wrapper.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE item_type ADD VALUE IF NOT EXISTS 'note'")


def downgrade() -> None:
    # Postgres has no ALTER TYPE ... DROP VALUE — removing an enum value
    # requires rebuilding the type, which isn't worth it for a downgrade
    # path. Leaving 'note' in the enum on downgrade is harmless (unused
    # value), just not reversed.
    pass

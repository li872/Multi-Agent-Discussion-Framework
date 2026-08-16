"""add token_usages table

Revision ID: c9f1a2b3d4e5
Revises: ab1a621f72a1
Create Date: 2026-08-16 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c9f1a2b3d4e5"
down_revision: Union[str, Sequence[str], None] = "ab1a621f72a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "token_usages",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("discussion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="llm"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["discussion_id"], ["discussions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_tu_user_created", "token_usages", ["user_id", "created_at"])
    op.create_index("idx_tu_discussion_created", "token_usages", ["discussion_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_tu_discussion_created", table_name="token_usages")
    op.drop_index("idx_tu_user_created", table_name="token_usages")
    op.drop_table("token_usages")

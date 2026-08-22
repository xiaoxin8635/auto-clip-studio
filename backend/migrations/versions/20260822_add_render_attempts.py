"""add segment render attempts

Revision ID: 0001
Revises:
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("segments")}
    if "render_attempts" not in columns:
        op.add_column("segments", sa.Column("render_attempts", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("segments", "render_attempts")

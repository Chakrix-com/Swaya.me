"""add is_required to questions

Revision ID: e3f4a5b6c7d8
Revises: 20260329_1505
Create Date: 2026-04-14 09:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "1e82c6f2b913"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("questions")}
    if "is_required" not in columns:
        op.add_column(
            "questions",
            sa.Column("is_required", sa.Boolean(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("questions")}
    if "is_required" in columns:
        op.drop_column("questions", "is_required")

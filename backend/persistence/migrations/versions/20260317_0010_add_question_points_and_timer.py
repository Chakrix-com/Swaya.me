"""add question points and timer

Revision ID: c9d8e7f6a5b4
Revises: 754b41adddfe
Create Date: 2026-03-17 00:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, None] = "754b41adddfe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("questions")}

    if "points" not in columns:
        op.add_column(
            "questions",
            sa.Column("points", sa.Integer(), nullable=False, server_default="1"),
        )
    if "max_time_seconds" not in columns:
        op.add_column(
            "questions",
            sa.Column("max_time_seconds", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("questions")}

    if "max_time_seconds" in columns:
        op.drop_column("questions", "max_time_seconds")
    if "points" in columns:
        op.drop_column("questions", "points")

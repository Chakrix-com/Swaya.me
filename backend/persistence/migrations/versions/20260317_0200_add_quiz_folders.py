"""add nested quiz folders

Revision ID: b8c7d6e5f4a3
Revises: c9d8e7f6a5b4
Create Date: 2026-03-17 02:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8c7d6e5f4a3"
down_revision: Union[str, None] = "c9d8e7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "quiz_folders" not in tables:
        op.create_table(
            "quiz_folders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("parent_id", sa.Integer(), sa.ForeignKey("quiz_folders.id", ondelete="CASCADE"), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("tenant_id", "parent_id", "name", name="uq_quiz_folders_tenant_parent_name"),
        )
        op.create_index("ix_quiz_folders_tenant_id", "quiz_folders", ["tenant_id"])
        op.create_index("ix_quiz_folders_parent_id", "quiz_folders", ["parent_id"])

    quiz_columns = {col["name"] for col in inspector.get_columns("quizzes")}
    if "folder_id" not in quiz_columns:
        op.add_column("quizzes", sa.Column("folder_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_quizzes_folder_id",
            "quizzes",
            "quiz_folders",
            ["folder_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_quizzes_folder_id", "quizzes", ["folder_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    quiz_columns = {col["name"] for col in inspector.get_columns("quizzes")}
    if "folder_id" in quiz_columns:
        try:
            op.drop_index("ix_quizzes_folder_id", table_name="quizzes")
        except Exception:
            pass
        try:
            op.drop_constraint("fk_quizzes_folder_id", "quizzes", type_="foreignkey")
        except Exception:
            pass
        op.drop_column("quizzes", "folder_id")

    tables = set(inspector.get_table_names())
    if "quiz_folders" in tables:
        try:
            op.drop_index("ix_quiz_folders_parent_id", table_name="quiz_folders")
        except Exception:
            pass
        try:
            op.drop_index("ix_quiz_folders_tenant_id", table_name="quiz_folders")
        except Exception:
            pass
        op.drop_table("quiz_folders")

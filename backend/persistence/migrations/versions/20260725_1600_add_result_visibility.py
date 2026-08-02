"""add result_visibility column to questions (host-configurable candidate-facing result reveal level)

Revision ID: 20260725_1600
Revises: 20260725_0900
Create Date: 2026-07-25 16:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20260725_1600'
down_revision = '20260725_0900'
branch_labels = None
depends_on = None

_ENUM_VALUES = ('hidden', 'status_only', 'full')


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    question_columns = {col["name"] for col in inspector.get_columns("questions")}
    if "result_visibility" not in question_columns:
        op.add_column(
            'questions',
            sa.Column(
                'result_visibility',
                sa.Enum(*_ENUM_VALUES, name='codingresultvisibility'),
                nullable=False,
                server_default='hidden',
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    question_columns = {col["name"] for col in inspector.get_columns("questions")}
    if "result_visibility" in question_columns:
        op.drop_column('questions', 'result_visibility')

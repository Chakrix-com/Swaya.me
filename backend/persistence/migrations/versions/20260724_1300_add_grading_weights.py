"""add grading_weights column to questions (host-overridable coding-challenge scoring weights)

Revision ID: 20260724_1300
Revises: 20260724_1200
Create Date: 2026-07-24 13:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20260724_1300'
down_revision = '20260724_1200'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    question_columns = {col["name"] for col in inspector.get_columns("questions")}
    if "grading_weights" not in question_columns:
        op.add_column('questions', sa.Column('grading_weights', sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    question_columns = {col["name"] for col in inspector.get_columns("questions")}
    if "grading_weights" in question_columns:
        op.drop_column('questions', 'grading_weights')

"""add mcq_multi question type with multi-select columns

Revision ID: 20260714_1000
Revises: 20260705_1200
Create Date: 2026-07-14 10:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20260714_1000'
down_revision = '20260705_1200'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE questions "
        "MODIFY COLUMN question_type "
        "ENUM('mcq','word_cloud','single_line','scale','paragraph','one_word','code','mcq_multi') "
        "NOT NULL"
    )
    op.add_column('questions', sa.Column('correct_answer_indices', sa.JSON(), nullable=True))
    op.add_column('questions', sa.Column('reveal_answer_count', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('answers', sa.Column('selected_option_indices', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('answers', 'selected_option_indices')
    op.drop_column('questions', 'reveal_answer_count')
    op.drop_column('questions', 'correct_answer_indices')
    op.execute(
        "ALTER TABLE questions "
        "MODIFY COLUMN question_type "
        "ENUM('mcq','word_cloud','single_line','scale','paragraph','one_word','code') "
        "NOT NULL"
    )

"""add_word_cloud_question_type

Revision ID: 035ab11d95fd
Revises: 7a3e644628bd
Create Date: 2026-02-13 23:47:37.848837

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '035ab11d95fd'
down_revision: Union[str, None] = '7a3e644628bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add question_type enum
    op.execute("ALTER TABLE questions ADD COLUMN question_type ENUM('mcq', 'word_cloud') NOT NULL DEFAULT 'mcq'")
    
    # Make options and correct_answer_index nullable for word_cloud questions
    op.alter_column('questions', 'options', nullable=True, existing_type=sa.JSON())
    op.alter_column('questions', 'correct_answer_index', nullable=True, existing_type=sa.Integer())
    
    # Add text_answer column to answers table for word_cloud responses
    op.add_column('answers', sa.Column('text_answer', sa.String(100), nullable=True))
    
    # Make selected_option_index and is_correct nullable
    op.alter_column('answers', 'selected_option_index', nullable=True, existing_type=sa.Integer())
    op.alter_column('answers', 'is_correct', nullable=True, existing_type=sa.Boolean())


def downgrade() -> None:
    # Remove text_answer column
    op.drop_column('answers', 'text_answer')
    
    # Make selected_option_index and is_correct non-nullable again
    op.alter_column('answers', 'is_correct', nullable=False, existing_type=sa.Boolean())
    op.alter_column('answers', 'selected_option_index', nullable=False, existing_type=sa.Integer())
    
    # Make options and correct_answer_index non-nullable again
    op.alter_column('questions', 'correct_answer_index', nullable=False, existing_type=sa.Integer())
    op.alter_column('questions', 'options', nullable=False, existing_type=sa.JSON())
    
    # Remove question_type column
    op.drop_column('questions', 'question_type')

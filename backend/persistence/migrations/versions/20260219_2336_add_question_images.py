"""add_question_images

Revision ID: 8f2c9a4b1e3d
Revises: 035ab11d95fd
Create Date: 2026-02-19 23:36:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f2c9a4b1e3d'
down_revision: Union[str, None] = '035ab11d95fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add question_image_url column for question text image
    op.add_column('questions', sa.Column('question_image_url', sa.String(500), nullable=True))
    
    # Add option_images column for MCQ option images (JSON dict: {"A": "path", "B": "path", ...})
    op.add_column('questions', sa.Column('option_images', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove option_images column
    op.drop_column('questions', 'option_images')
    
    # Remove question_image_url column
    op.drop_column('questions', 'question_image_url')

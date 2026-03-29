"""add_created_by_id_to_quiz_folders

Revision ID: 1e82c6f2b913
Revises: 20260324_1000
Create Date: 2026-03-29 15:05:23.226655

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '1e82c6f2b913'
down_revision: Union[str, None] = '20260324_1000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('quiz_folders', sa.Column('created_by_id', sa.Integer(), nullable=True))
    op.create_index('ix_quiz_folders_created_by_id', 'quiz_folders', ['created_by_id'], unique=False)
    op.create_foreign_key(
        'fk_quiz_folders_created_by_id', 'quiz_folders', 'users',
        ['created_by_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_quiz_folders_created_by_id', 'quiz_folders', type_='foreignkey')
    op.drop_index('ix_quiz_folders_created_by_id', table_name='quiz_folders')
    op.drop_column('quiz_folders', 'created_by_id')

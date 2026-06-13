"""add_folder_shares

Revision ID: 20260613_1400
Revises: 20260613_1200
Create Date: 2026-06-13 14:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20260613_1400'
down_revision = '20260613_1200'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'folder_shares',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('folder_id', sa.Integer(), sa.ForeignKey('quiz_folders.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('shared_with_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('can_edit', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('folder_id', 'shared_with_user_id', name='uq_folder_shares'),
    )


def downgrade():
    op.drop_table('folder_shares')

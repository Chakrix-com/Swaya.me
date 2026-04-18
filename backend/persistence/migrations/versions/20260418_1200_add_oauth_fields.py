"""add oauth fields for social login

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-04-18 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('oauth_provider', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('oauth_provider_id', sa.String(255), nullable=True))
    op.alter_column('users', 'hashed_password', existing_type=sa.String(255), nullable=True)
    op.create_index('ix_users_oauth_provider_id', 'users', ['oauth_provider', 'oauth_provider_id'])


def downgrade() -> None:
    op.drop_index('ix_users_oauth_provider_id', table_name='users')
    op.drop_column('users', 'oauth_provider_id')
    op.drop_column('users', 'oauth_provider')
    op.alter_column('users', 'hashed_password', existing_type=sa.String(255), nullable=False)

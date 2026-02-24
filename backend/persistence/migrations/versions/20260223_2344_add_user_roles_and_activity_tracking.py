"""add_user_roles_and_activity_tracking

Revision ID: 7577cf61d0b7
Revises: 8f2c9a4b1e3d
Create Date: 2026-02-23 23:44:06.036311

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7577cf61d0b7'
down_revision: Union[str, None] = '8f2c9a4b1e3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add role column to users table (MySQL ENUM is defined inline)
    op.add_column('users', sa.Column('role', sa.Enum('super_admin', 'admin', 'user', 'viewer', name='user_role'), nullable=False, server_default='user'))
    
    # Add activity tracking columns
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('login_count', sa.Integer, nullable=False, server_default='0'))
    
    # Set first user (ID=1) as super_admin if exists
    op.execute("UPDATE users SET role = 'super_admin' WHERE id = 1")
    
    # Create user_activities table for audit logging
    op.create_table(
        'user_activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE')
    )
    
    # Add indexes for performance
    op.create_index('ix_user_activities_user_id', 'user_activities', ['user_id'])
    op.create_index('ix_user_activities_tenant_id', 'user_activities', ['tenant_id'])
    op.create_index('ix_user_activities_action', 'user_activities', ['action'])
    op.create_index('ix_user_activities_created_at', 'user_activities', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_user_activities_created_at', 'user_activities')
    op.drop_index('ix_user_activities_action', 'user_activities')
    op.drop_index('ix_user_activities_tenant_id', 'user_activities')
    op.drop_index('ix_user_activities_user_id', 'user_activities')
    
    # Drop user_activities table
    op.drop_table('user_activities')
    
    # Remove activity tracking columns
    op.drop_column('users', 'login_count')
    op.drop_column('users', 'last_login_at')
    
    # Remove role column (MySQL ENUM is dropped with column)
    op.drop_column('users', 'role')

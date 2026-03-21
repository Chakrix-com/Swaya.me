"""add admin quota system

Revision ID: f7g8h9i0j1k2
Revises: a1b2c3d4e5f6
Create Date: 2026-02-24 08:29:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'f7g8h9i0j1k2'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add per-admin quota system:
    - user_quota: quota limit for each admin
    - managed_by_admin_id: tracks which admin owns each user
    - Create NO-ORG tenant for self-registered users
    """
    # Add user_quota column (for admin users only)
    op.add_column('users', sa.Column('user_quota', sa.Integer(), nullable=True))
    
    # Add managed_by_admin_id column (foreign key to users table)
    op.add_column('users', sa.Column('managed_by_admin_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_users_managed_by_admin',
        'users', 'users',
        ['managed_by_admin_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add index for performance
    op.create_index('idx_users_managed_by', 'users', ['managed_by_admin_id'])
    
    # Create NO-ORG tenant (id=1) if it doesn't exist
    # Note: This uses raw SQL to ensure consistent tenant_id=1
    op.execute("""
        INSERT INTO tenants (id, name, slug, tier, is_active, created_at, updated_at)
        SELECT 1, 'NO-ORG', 'no-org', 'free', 1, NOW(), NOW()
        WHERE NOT EXISTS (SELECT 1 FROM tenants WHERE id = 1)
    """)
    
    # Set default quota for existing admin users (50 users - generous for existing)
    op.execute("""
        UPDATE users 
        SET user_quota = 50 
        WHERE role = 'admin' AND user_quota IS NULL
    """)
    
    # Assign existing regular users to first admin in their tenant
    # This is a best-effort assignment for data migration
    op.execute("""
        UPDATE users u1
        JOIN (
            SELECT u.id as user_id, 
                   (SELECT id FROM users WHERE tenant_id = u.tenant_id AND role = 'admin' ORDER BY id LIMIT 1) as admin_id
            FROM users u
            WHERE u.role = 'user' AND u.managed_by_admin_id IS NULL
        ) assignments ON u1.id = assignments.user_id
        SET u1.managed_by_admin_id = assignments.admin_id
        WHERE assignments.admin_id IS NOT NULL
    """)


def downgrade() -> None:
    """Remove quota system changes"""
    # Drop index
    op.drop_index('idx_users_managed_by', table_name='users')
    
    # Drop foreign key
    op.drop_constraint('fk_users_managed_by_admin', 'users', type_='foreignkey')
    
    # Drop columns
    op.drop_column('users', 'managed_by_admin_id')
    op.drop_column('users', 'user_quota')
    
    # Note: We do NOT delete NO-ORG tenant to avoid data loss
    # Manual cleanup required if needed

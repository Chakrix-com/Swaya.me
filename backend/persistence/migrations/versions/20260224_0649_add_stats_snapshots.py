"""Add stats_snapshots table for historical tracking

Revision ID: a1b2c3d4e5f6
Revises: 7577cf61d0b7
Create Date: 2026-02-24 06:49:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '7577cf61d0b7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'stats_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('captured_at', sa.DateTime(), nullable=False),
        sa.Column('granularity', sa.Enum('HOURLY', 'DAILY', name='snapshotgranularity'), nullable=False),
        sa.Column('scope', sa.Enum('PLATFORM', 'TENANT', name='snapshotscope'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('stats_data', mysql.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    op.create_index('idx_captured_at', 'stats_snapshots', ['captured_at'], unique=False)
    op.create_index('idx_scope_tenant', 'stats_snapshots', ['scope', 'tenant_id'], unique=False)
    op.create_index('idx_granularity', 'stats_snapshots', ['granularity'], unique=False)
    op.create_index('idx_composite', 'stats_snapshots', ['scope', 'tenant_id', 'granularity', 'captured_at'], unique=False)


def downgrade():
    op.drop_index('idx_composite', table_name='stats_snapshots')
    op.drop_index('idx_granularity', table_name='stats_snapshots')
    op.drop_index('idx_scope_tenant', table_name='stats_snapshots')
    op.drop_index('idx_captured_at', table_name='stats_snapshots')
    op.drop_table('stats_snapshots')

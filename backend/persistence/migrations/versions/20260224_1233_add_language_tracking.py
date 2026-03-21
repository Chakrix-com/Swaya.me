"""Add language tracking

Revision ID: 20260224_1233
Revises: 20260224_0829
Create Date: 2026-02-24 12:33:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'l3m4n5o6p7q8'
down_revision = 'f7g8h9i0j1k2'
branch_labels = None
depends_on = None


def upgrade():
    # Add language_preference column to users table
    op.add_column('users', 
        sa.Column('language_preference', sa.String(10), nullable=False, server_default='en')
    )
    
    # Create language_usage_events table
    op.create_table(
        'language_usage_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('previous_language', sa.String(10), nullable=True),
        sa.Column('event_type', sa.Enum('change', 'initial', name='event_type_enum'), nullable=False, server_default='change'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='SET NULL')
    )
    
    # Create indexes for performance
    op.create_index('idx_language_events_user_id', 'language_usage_events', ['user_id'])
    op.create_index('idx_language_events_session_id', 'language_usage_events', ['session_id'])
    op.create_index('idx_language_events_created_at', 'language_usage_events', ['created_at'])
    op.create_index('idx_language_events_language', 'language_usage_events', ['language'])
    op.create_index('idx_language_events_tenant_id', 'language_usage_events', ['tenant_id'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_language_events_tenant_id', table_name='language_usage_events')
    op.drop_index('idx_language_events_language', table_name='language_usage_events')
    op.drop_index('idx_language_events_created_at', table_name='language_usage_events')
    op.drop_index('idx_language_events_session_id', table_name='language_usage_events')
    op.drop_index('idx_language_events_user_id', table_name='language_usage_events')
    
    # Drop table
    op.drop_table('language_usage_events')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS event_type_enum')
    
    # Drop column from users
    op.drop_column('users', 'language_preference')

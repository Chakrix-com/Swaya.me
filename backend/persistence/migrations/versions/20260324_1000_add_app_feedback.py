"""Add app_feedback table for global app feedback

Revision ID: 20260324_1000
Revises: 20260323_0900
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260324_1000'
down_revision = '20260323_0900'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'app_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('page_url', sa.String(500), nullable=False),
        sa.Column('feedback_text', sa.Text(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('source_type', sa.String(20), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    op.create_index('idx_app_feedback_id', 'app_feedback', ['id'], unique=True)
    op.create_index('idx_app_feedback_user_id', 'app_feedback', ['user_id'], unique=False)
    op.create_index('idx_app_feedback_tenant_id', 'app_feedback', ['tenant_id'], unique=False)
    op.create_index('idx_app_feedback_created_at', 'app_feedback', ['created_at'], unique=False)


def downgrade():
    op.drop_index('idx_app_feedback_created_at', table_name='app_feedback')
    op.drop_index('idx_app_feedback_tenant_id', table_name='app_feedback')
    op.drop_index('idx_app_feedback_user_id', table_name='app_feedback')
    op.drop_index('idx_app_feedback_id', table_name='app_feedback')
    op.drop_table('app_feedback')

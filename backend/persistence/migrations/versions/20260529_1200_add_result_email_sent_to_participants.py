"""add result_email_sent to participants

Revision ID: 20260529_1200
Revises: 20260524_1300
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = '20260529_1200'
down_revision = 'i6j7k8l9m0n1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'participants',
        sa.Column('result_email_sent', sa.Boolean(), nullable=False, server_default='0')
    )


def downgrade():
    op.drop_column('participants', 'result_email_sent')

"""add certificate_token to participants

Revision ID: 20260625_1200
Revises: 20260618_1800
Create Date: 2026-06-25 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20260625_1200'
down_revision = '20260618_1800'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('participants', sa.Column('certificate_token', sa.String(36), nullable=True))
    op.create_unique_constraint('uq_participants_certificate_token', 'participants', ['certificate_token'])
    op.create_index('ix_participants_certificate_token', 'participants', ['certificate_token'], unique=True)


def downgrade():
    op.drop_index('ix_participants_certificate_token', table_name='participants')
    op.drop_constraint('uq_participants_certificate_token', 'participants', type_='unique')
    op.drop_column('participants', 'certificate_token')

"""add app_feedback.attachments (screenshot filenames)

Revision ID: 20261022_1000
Revises: 20261021_1000
Create Date: 2026-10-22 10:00:00

Screenshots attached to global feedback are stored privately under
<uploads>/feedback/<id>/; this column lists their filenames.
"""
from alembic import op
import sqlalchemy as sa

revision = '20261022_1000'
down_revision = '20261021_1000'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('app_feedback', sa.Column('attachments', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('app_feedback', 'attachments')

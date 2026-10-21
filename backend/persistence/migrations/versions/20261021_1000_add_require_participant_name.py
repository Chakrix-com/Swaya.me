"""add quizzes.require_participant_name

Revision ID: 20261021_1000
Revises: 20260906_1000
Create Date: 2026-10-21 10:00:00

Host option for live quizzes/polls: when on, the join screen offers no random
"creative" name and the backend refuses a blank display name. Defaults to off,
so existing quizzes keep today's behaviour.
"""
from alembic import op
import sqlalchemy as sa

revision = '20261021_1000'
down_revision = '20260906_1000'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('quizzes', sa.Column('require_participant_name', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('quizzes', 'require_participant_name')

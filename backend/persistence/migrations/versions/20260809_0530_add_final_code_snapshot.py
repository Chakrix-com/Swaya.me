"""add final_code_snapshot to code_submissions

Revision ID: 20260809_0530
Revises: 20260803_0417
Create Date: 2026-08-09 05:30:00

Part of the deterministic-first grading redesign (2026-08-09): code_quality
and architecture are now AI-judged from the FINAL code state at submission
time, not the full `git log -p` commit history — smaller (bounded by repo
size, not session length), more relevant (judging the actual submitted code,
not reconstructing it from a diff timeline), and what actually fixes the
huge-context problem at its root rather than just truncating a giant dump.
Nullable — existing submissions harvested before this migration simply won't
have one (grading_service_async.py falls back to code_timeline for those).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '20260809_0530'
down_revision = '20260803_0417'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'code_submissions',
        sa.Column('final_code_snapshot', mysql.LONGTEXT(), nullable=True),
    )


def downgrade():
    op.drop_column('code_submissions', 'final_code_snapshot')

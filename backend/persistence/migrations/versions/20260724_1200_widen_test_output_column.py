"""widen code_submissions.test_output from TEXT to LONGTEXT

Found live during Phase 11's Selenium walkthrough: a real, non-quiet `mvn test`
run produces well over 64KB of ANSI-colored build output, exceeding plain TEXT's
capacity (asyncmy DataError 1406 "Data too long for column 'test_output'") and
crashing the grading job's final commit with no error handling around it,
permanently stranding the submission at `grading`. Its sibling columns
(ai_transcript_raw, code_timeline) already correctly use LONGTEXT — this one
was the outlier.

Revision ID: 20260724_1200
Revises: 20260724_1000
Create Date: 2026-07-24 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import LONGTEXT as MYSQL_LONGTEXT

revision = '20260724_1200'
down_revision = '20260724_1000'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'code_submissions', 'test_output',
        existing_type=sa.Text(),
        type_=MYSQL_LONGTEXT(),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        'code_submissions', 'test_output',
        existing_type=MYSQL_LONGTEXT(),
        type_=sa.Text(),
        existing_nullable=True,
    )

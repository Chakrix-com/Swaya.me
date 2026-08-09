"""add grading_mode selector (host-configurable AI-judged/hybrid/deterministic)

Revision ID: 20260809_0900
Revises: 20260809_0530
Create Date: 2026-08-09 09:00:00

Part of the grading-mode-selector redesign (see
_private/coding_challenge_grading_mode_plan_20260809.md): hosts can now pick
how code_quality/architecture/ai_usage_efficiency/prompt_quality get scored
per question. Adds three columns:

- questions.grading_mode — the host's choice, default 'hybrid' (mirrors the
  existing grading_weights override pattern).
- code_submissions.static_analysis_result — harvested once while the
  workspace is still alive (regrade_submission has no live workspace), so
  hybrid/deterministic scoring never needs to re-exec into a destroyed
  workspace on regrade.
- code_submissions.grading_mode_used — the mode actually applied when a
  submission was scored, captured independently of questions.grading_mode
  (which a host can edit after candidates are already graded) so regrades
  stay consistent with the original grading attempt. NULL on every
  submission that predates this migration.
"""
from alembic import op
import sqlalchemy as sa

revision = '20260809_0900'
down_revision = '20260809_0530'
branch_labels = None
depends_on = None

_ENUM_VALUES = ('ai_judged', 'hybrid', 'deterministic')


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    question_columns = {col["name"] for col in inspector.get_columns("questions")}
    if "grading_mode" not in question_columns:
        op.add_column(
            'questions',
            sa.Column(
                'grading_mode',
                sa.Enum(*_ENUM_VALUES, name='gradingmode'),
                nullable=False,
                server_default='hybrid',
            ),
        )

    submission_columns = {col["name"] for col in inspector.get_columns("code_submissions")}
    if "static_analysis_result" not in submission_columns:
        op.add_column(
            'code_submissions',
            sa.Column('static_analysis_result', sa.JSON(), nullable=True),
        )
    if "grading_mode_used" not in submission_columns:
        op.add_column(
            'code_submissions',
            # MySQL ENUM columns are inline per-column (no shared DB-level type
            # the way Postgres has), so this just declares its own ENUM(...)
            # with the same 3 values as questions.grading_mode above — the
            # matching `name=` is for SQLAlchemy's own metadata bookkeeping only.
            sa.Column(
                'grading_mode_used',
                sa.Enum(*_ENUM_VALUES, name='gradingmode'),
                nullable=True,
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    submission_columns = {col["name"] for col in inspector.get_columns("code_submissions")}
    if "grading_mode_used" in submission_columns:
        op.drop_column('code_submissions', 'grading_mode_used')
    if "static_analysis_result" in submission_columns:
        op.drop_column('code_submissions', 'static_analysis_result')

    question_columns = {col["name"] for col in inspector.get_columns("questions")}
    if "grading_mode" in question_columns:
        op.drop_column('questions', 'grading_mode')

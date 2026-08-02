"""add attempt_number to code_workspaces (host-granted re-invite support)

Revision ID: 20260729_1100
Revises: 20260725_1600
Create Date: 2026-07-29 11:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20260729_1100'
down_revision = '20260725_1600'
branch_labels = None
depends_on = None

_OLD_CONSTRAINT = 'uq_code_workspace_quiz_question_email'
_NEW_CONSTRAINT = 'uq_code_workspace_quiz_question_email_attempt'


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("code_workspaces")}
    if "attempt_number" not in columns:
        op.add_column(
            'code_workspaces',
            sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        )

    invite_columns = {col["name"] for col in inspector.get_columns("coding_challenge_invites")}
    if "latest_invited_attempt_number" not in invite_columns:
        op.add_column(
            'coding_challenge_invites',
            sa.Column('latest_invited_attempt_number', sa.Integer(), nullable=False, server_default='1'),
        )

    constraint_names = {uc["name"] for uc in inspector.get_unique_constraints("code_workspaces")}
    if _OLD_CONSTRAINT in constraint_names:
        op.drop_constraint(_OLD_CONSTRAINT, 'code_workspaces', type_='unique')

    inspector = sa.inspect(bind)
    constraint_names = {uc["name"] for uc in inspector.get_unique_constraints("code_workspaces")}
    if _NEW_CONSTRAINT not in constraint_names:
        op.create_unique_constraint(
            _NEW_CONSTRAINT, 'code_workspaces',
            ['quiz_id', 'question_id', 'candidate_email', 'attempt_number'],
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraint_names = {uc["name"] for uc in inspector.get_unique_constraints("code_workspaces")}
    if _NEW_CONSTRAINT in constraint_names:
        op.drop_constraint(_NEW_CONSTRAINT, 'code_workspaces', type_='unique')

    inspector = sa.inspect(bind)
    constraint_names = {uc["name"] for uc in inspector.get_unique_constraints("code_workspaces")}
    if _OLD_CONSTRAINT not in constraint_names:
        op.create_unique_constraint(
            _OLD_CONSTRAINT, 'code_workspaces',
            ['quiz_id', 'question_id', 'candidate_email'],
        )

    columns = {col["name"] for col in inspector.get_columns("code_workspaces")}
    if "attempt_number" in columns:
        op.drop_column('code_workspaces', 'attempt_number')

    invite_columns = {col["name"] for col in inspector.get_columns("coding_challenge_invites")}
    if "latest_invited_attempt_number" in invite_columns:
        op.drop_column('coding_challenge_invites', 'latest_invited_attempt_number')

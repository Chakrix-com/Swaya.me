"""add coding_challenge_invites table (tracks invited candidates for batch invite + pending-invites list)

Revision ID: 20260725_0900
Revises: 20260724_1300
Create Date: 2026-07-25 09:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20260725_0900'
down_revision = '20260724_1300'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'coding_challenge_invites' not in inspector.get_table_names():
        op.create_table(
            'coding_challenge_invites',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False, index=True),
            sa.Column('quiz_id', sa.Integer(), sa.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('question_id', sa.Integer(), sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('candidate_email', sa.String(255), nullable=False, index=True),
            sa.Column('invited_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('email_sent', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('quiz_id', 'question_id', 'candidate_email', name='uq_cc_invite_quiz_question_email'),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'coding_challenge_invites' in inspector.get_table_names():
        op.drop_table('coding_challenge_invites')

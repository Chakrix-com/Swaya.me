"""Add quiz feedback table

Revision ID: q1w2e3r4t5y6
Revises: l3m4n5o6p7q8
Create Date: 2026-02-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'q1w2e3r4t5y6'
down_revision = 'l3m4n5o6p7q8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'quiz_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('participant_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('feedback_text', sa.Text(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['participant_id'], ['participants.id']),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id']),
        sa.ForeignKeyConstraint(['session_id'], ['quiz_sessions.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_quiz_feedback_quiz_id', 'quiz_feedback', ['quiz_id'])
    op.create_index('idx_quiz_feedback_session_id', 'quiz_feedback', ['session_id'])
    op.create_index('idx_quiz_feedback_participant_id', 'quiz_feedback', ['participant_id'])
    op.create_index('idx_quiz_feedback_user_id', 'quiz_feedback', ['user_id'])
    op.create_index('idx_quiz_feedback_tenant_id', 'quiz_feedback', ['tenant_id'])
    op.create_index('idx_quiz_feedback_created_at', 'quiz_feedback', ['created_at'])


def downgrade():
    op.drop_index('idx_quiz_feedback_created_at', table_name='quiz_feedback')
    op.drop_index('idx_quiz_feedback_tenant_id', table_name='quiz_feedback')
    op.drop_index('idx_quiz_feedback_user_id', table_name='quiz_feedback')
    op.drop_index('idx_quiz_feedback_participant_id', table_name='quiz_feedback')
    op.drop_index('idx_quiz_feedback_session_id', table_name='quiz_feedback')
    op.drop_index('idx_quiz_feedback_quiz_id', table_name='quiz_feedback')
    op.drop_table('quiz_feedback')

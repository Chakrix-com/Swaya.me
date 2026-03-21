"""Add session_question_timings table

Revision ID: r2s3t4u5v6w7
Revises: q1w2e3r4t5y6
Create Date: 2026-03-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'r2s3t4u5v6w7'
down_revision = 'q1w2e3r4t5y6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'session_question_timings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('question_index', sa.Integer(), nullable=False),
        sa.Column('opened_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['quiz_sessions.id']),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sqt_session_id', 'session_question_timings', ['session_id'])
    op.create_index('idx_sqt_question_id', 'session_question_timings', ['question_id'])


def downgrade():
    op.drop_index('idx_sqt_question_id', table_name='session_question_timings')
    op.drop_index('idx_sqt_session_id', table_name='session_question_timings')
    op.drop_table('session_question_timings')

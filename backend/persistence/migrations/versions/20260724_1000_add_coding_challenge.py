"""add coding_challenge quiz/question type, Question fields, code_workspaces/code_submissions tables

Revision ID: 20260724_1000
Revises: 20260714_1000
Create Date: 2026-07-24 10:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME, LONGTEXT as MYSQL_LONGTEXT

revision = '20260724_1000'
down_revision = '20260714_1000'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. quiz_type ENUM: add 'coding_challenge'
    bind.execute(sa.text(
        "ALTER TABLE quizzes MODIFY COLUMN quiz_type "
        "ENUM('quiz','poll','offline_poll','exam','coding_challenge') NOT NULL DEFAULT 'quiz'"
    ))

    # 2. question_type ENUM: add 'coding_challenge'
    bind.execute(sa.text(
        "ALTER TABLE questions MODIFY COLUMN question_type "
        "ENUM('mcq','word_cloud','single_line','scale','paragraph','one_word','code','mcq_multi','coding_challenge') "
        "NOT NULL"
    ))

    # 3. New Question columns for CODING_CHALLENGE
    question_columns = {col["name"] for col in inspector.get_columns("questions")}
    if "git_repo_url" not in question_columns:
        op.add_column('questions', sa.Column('git_repo_url', sa.String(500), nullable=True))
    if "test_command" not in question_columns:
        op.add_column('questions', sa.Column(
            'test_command', sa.String(255), nullable=True, server_default='pytest -q'
        ))
    if "hidden_test_content" not in question_columns:
        op.add_column('questions', sa.Column('hidden_test_content', sa.Text(), nullable=True))
    if "hidden_test_filename" not in question_columns:
        op.add_column('questions', sa.Column('hidden_test_filename', sa.String(255), nullable=True))
    if "time_budget_seconds" not in question_columns:
        op.add_column('questions', sa.Column('time_budget_seconds', sa.Integer(), nullable=True))

    # 4. code_workspaces table
    if not inspector.has_table("code_workspaces"):
        op.create_table(
            'code_workspaces',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False, index=True),
            sa.Column('quiz_id', sa.Integer(), sa.ForeignKey('quizzes.id'), nullable=False, index=True),
            sa.Column('question_id', sa.Integer(), sa.ForeignKey('questions.id'), nullable=False, index=True),
            sa.Column('candidate_email', sa.String(255), nullable=False, index=True),
            sa.Column('ide_type', sa.String(20), nullable=False),
            sa.Column('coder_workspace_name', sa.String(255), nullable=False, unique=True),
            sa.Column('coder_token_name', sa.String(255), nullable=True),
            sa.Column(
                'status',
                sa.Enum('provisioning', 'active', 'submitted', 'abandoned', 'destroyed', name='codeworkspacestatus'),
                nullable=False, server_default='provisioning',
            ),
            sa.Column('workspace_url', sa.String(1000), nullable=True),
            sa.Column('submitted_at', MYSQL_DATETIME(fsp=6), nullable=True),
            sa.Column('destroyed_at', MYSQL_DATETIME(fsp=6), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('quiz_id', 'question_id', 'candidate_email', name='uq_code_workspace_quiz_question_email'),
        )

    # 5. code_submissions table
    if not inspector.has_table("code_submissions"):
        op.create_table(
            'code_submissions',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('code_workspaces.id'), nullable=False, index=True),
            sa.Column('question_id', sa.Integer(), sa.ForeignKey('questions.id'), nullable=False, index=True),
            sa.Column('test_output', sa.Text(), nullable=True),
            sa.Column('passed_count', sa.Integer(), nullable=True),
            sa.Column('total_count', sa.Integer(), nullable=True),
            sa.Column('ai_transcript_raw', MYSQL_LONGTEXT, nullable=True),
            sa.Column('code_timeline', MYSQL_LONGTEXT, nullable=True),
            sa.Column('ai_token_usage', sa.JSON(), nullable=True),
            sa.Column('score_breakdown', sa.JSON(), nullable=True),
            sa.Column('ai_score', sa.Integer(), nullable=True),
            sa.Column('ai_verdict', sa.String(50), nullable=True),
            sa.Column('ai_rationale', sa.Text(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column(
                'status',
                sa.Enum('queued', 'grading', 'graded', 'failed', 'partial_failed', name='codesubmissionstatus'),
                nullable=False, server_default='queued',
            ),
            sa.Column('submitted_at', MYSQL_DATETIME(fsp=6), nullable=True),
            sa.Column('graded_at', MYSQL_DATETIME(fsp=6), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("code_submissions"):
        op.drop_table("code_submissions")

    if inspector.has_table("code_workspaces"):
        op.drop_table("code_workspaces")

    question_columns = {col["name"] for col in inspector.get_columns("questions")}
    if "time_budget_seconds" in question_columns:
        op.drop_column('questions', 'time_budget_seconds')
    if "hidden_test_filename" in question_columns:
        op.drop_column('questions', 'hidden_test_filename')
    if "hidden_test_content" in question_columns:
        op.drop_column('questions', 'hidden_test_content')
    if "test_command" in question_columns:
        op.drop_column('questions', 'test_command')
    if "git_repo_url" in question_columns:
        op.drop_column('questions', 'git_repo_url')

    bind.execute(sa.text(
        "ALTER TABLE questions MODIFY COLUMN question_type "
        "ENUM('mcq','word_cloud','single_line','scale','paragraph','one_word','code','mcq_multi') "
        "NOT NULL"
    ))

    bind.execute(sa.text(
        "ALTER TABLE quizzes MODIFY COLUMN quiz_type "
        "ENUM('quiz','poll','offline_poll','exam') NOT NULL DEFAULT 'quiz'"
    ))

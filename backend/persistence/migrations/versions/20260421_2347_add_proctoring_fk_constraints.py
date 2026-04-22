"""add_proctoring_fk_constraints

Revision ID: b7e8f9a0c1d2
Revises: 9d23bc5c3e6f
Create Date: 2026-04-21 23:47:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7e8f9a0c1d2'
down_revision: Union[str, None] = '9d23bc5c3e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # TenantProctoringPolicy
    op.create_foreign_key('fk_tenant_proctoring_policies_tenant_id', 'tenant_proctoring_policies', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    
    # ProctoringSession
    op.create_foreign_key('fk_proctoring_sessions_participant_id', 'proctoring_sessions', 'participants', ['participant_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_proctoring_sessions_quiz_id', 'proctoring_sessions', 'quizzes', ['quiz_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_proctoring_sessions_tenant_id', 'proctoring_sessions', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    
    # ProctoringEvent
    op.create_foreign_key('fk_proctoring_events_quiz_id', 'proctoring_events', 'quizzes', ['quiz_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_proctoring_events_tenant_id', 'proctoring_events', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_proctoring_events_participant_id', 'proctoring_events', 'participants', ['participant_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint('fk_proctoring_events_participant_id', 'proctoring_events', type_='foreignkey')
    op.drop_constraint('fk_proctoring_events_tenant_id', 'proctoring_events', type_='foreignkey')
    op.drop_constraint('fk_proctoring_events_quiz_id', 'proctoring_events', type_='foreignkey')
    
    op.drop_constraint('fk_proctoring_sessions_tenant_id', 'proctoring_sessions', type_='foreignkey')
    op.drop_constraint('fk_proctoring_sessions_quiz_id', 'proctoring_sessions', type_='foreignkey')
    op.drop_constraint('fk_proctoring_sessions_participant_id', 'proctoring_sessions', type_='foreignkey')
    
    op.drop_constraint('fk_tenant_proctoring_policies_tenant_id', 'tenant_proctoring_policies', type_='foreignkey')

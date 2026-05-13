"""add_email_to_participants

Revision ID: c9f1a2b3d4e5
Revises: b7e8f9a0c1d2
Create Date: 2026-05-13 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c9f1a2b3d4e5'
down_revision: Union[str, None] = 'b7e8f9a0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('participants', sa.Column('email', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('participants', 'email')

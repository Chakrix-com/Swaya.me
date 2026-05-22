"""fix_proctoring_browser_fingerprint_length

Revision ID: h5i6j7k8l9m0
Revises: g4h5i6j7k8l9
Create Date: 2026-05-22 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'h5i6j7k8l9m0'
down_revision: Union[str, None] = 'g4h5i6j7k8l9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'proctoring_sessions',
        'browser_fingerprint',
        existing_type=sa.String(64),
        type_=sa.String(512),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'proctoring_sessions',
        'browser_fingerprint',
        existing_type=sa.String(512),
        type_=sa.String(64),
        existing_nullable=True,
    )

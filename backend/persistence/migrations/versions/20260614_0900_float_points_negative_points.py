"""float points and negative_points in questions

Revision ID: 20260614_0900
Revises: 20260613_1400
Create Date: 2026-06-14 09:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = '20260614_0900'
down_revision = '20260613_1400'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('questions', 'points',
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=False,
        existing_server_default='1'
    )
    op.alter_column('questions', 'negative_points',
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=False,
        existing_server_default='0'
    )


def downgrade():
    op.alter_column('questions', 'negative_points',
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=False,
        existing_server_default='0'
    )
    op.alter_column('questions', 'points',
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=False,
        existing_server_default='1'
    )

"""Rich text question support — documentation only

This migration records the introduction of rich text (HTML) question content.
No DDL changes are needed: the existing TEXT column already supports up to 65 KB.
The max_length constraint was updated in the Pydantic schema (QuestionCreate,
QuestionUpdate) from 1 000 to 10 000 characters, and an XSS guard validator was
added to block <script>, <iframe>, and inline event handlers.

Revision ID: 20260322_1200
Revises: 20260322_1000
Create Date: 2026-03-22 12:00:00.000000
"""

# revision identifiers, used by Alembic.
revision = '20260322_1200'
down_revision = '20260322_1000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No DDL changes required.
    pass


def downgrade() -> None:
    # No DDL changes required.
    pass

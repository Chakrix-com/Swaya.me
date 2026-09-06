"""add users.password_changed_at (JWT-invalidation anchor for password reset)

Revision ID: 20260906_1000
Revises: 20260809_0900
Create Date: 2026-09-06 10:00:00

Security fix (LOW-2 in _private/vulnerability_audit_20260906.md): completing
a password reset previously did not revoke the account's other already-issued
JWTs — a stolen/leaked token kept authenticating normally after the
legitimate user reset their password in response to a suspected compromise.

Adds `users.password_changed_at` (nullable, defaults to NULL for existing
users so no currently-valid session is retroactively broken by this
migration). `execute_password_reset()` now stamps it on every successful
reset, and `core.auth.dependencies._resolve_token()` rejects any JWT whose
`iat` (issued-at) predates it — deliberately NOT reusing the existing
TimestampMixin `updated_at` column, since that column is bumped by
unrelated writes (login_count, last_login_at, tier changes, etc.) and would
have silently invalidated everyone's sessions on their next login.
"""
from alembic import op
import sqlalchemy as sa

revision = '20260906_1000'
down_revision = '20260809_0900'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {col["name"] for col in inspector.get_columns("users")}
    if "password_changed_at" not in user_columns:
        op.add_column(
            'users',
            sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {col["name"] for col in inspector.get_columns("users")}
    if "password_changed_at" in user_columns:
        op.drop_column('users', 'password_changed_at')

"""
Regression test for VULN-12 (hardcoded demo@swaya.me email-verification bypass).

login_user() used to special-case `demo@swaya.me` and skip the
is_email_verified check for that address alone — an unauthenticated
verification bypass. The fix removes the special case entirely; an
unverified account is rejected regardless of which email it is, and a
*verified* account (demo or otherwise) proceeds normally.

DB session is mocked (fixture ORM objects, not persisted) — matches the
existing pure-unit-test convention in this suite (see test_tier_override.py).
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from persistence.models.core import User, UserRole
from core.auth.service_async import login_user
from core.auth.schemas import UserLoginRequest
from shared.exceptions.auth import EmailNotVerifiedError


def _user(email: str, is_email_verified: bool, is_active: bool = True) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=1, tenant_id=1, email=email, hashed_password="irrelevant-mocked",
        role=UserRole.user, is_active=is_active, is_email_verified=is_email_verified,
        login_count=0, created_at=now, updated_at=now,
    )


def _db_returning(user):
    """Mock AsyncSession whose first select().execute() resolves to `user`."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
@pytest.mark.parametrize("email", ["demo@swaya.me", "someone.else@example.com"])
async def test_login_rejects_unverified_account_regardless_of_email(email):
    """No email — including demo@swaya.me — bypasses the verification check."""
    user = _user(email, is_email_verified=False)
    db = _db_returning(user)

    with patch("core.auth.service_async.verify_password", return_value=True):
        with pytest.raises(EmailNotVerifiedError):
            await login_user(db, UserLoginRequest(email=email, password="whatever"))


@pytest.mark.asyncio
async def test_login_does_not_raise_email_not_verified_for_verified_demo_account():
    """A *verified* demo account should proceed past the verification check
    (it may still fail later for unrelated reasons, e.g. no tenant mocked —
    the point is it must not be EmailNotVerifiedError)."""
    user = _user("demo@swaya.me", is_email_verified=True)
    db = _db_returning(user)

    with patch("core.auth.service_async.verify_password", return_value=True):
        try:
            await login_user(db, UserLoginRequest(email="demo@swaya.me", password="whatever"))
        except EmailNotVerifiedError:
            pytest.fail("verified demo account was rejected as unverified")
        except Exception:
            pass  # any other failure (e.g. missing tenant mock) is fine for this test

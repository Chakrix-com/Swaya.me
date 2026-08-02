"""
Unit tests for the "Coding Challenge Pro" per-user tier override feature:
- CurrentUser.effective_tier resolution (core/auth/dependencies.py)
- can_host_coding_challenge() helper
- coding-challenge creation gating in quiz_service_async
- tier_override handling in the user_management update_user service

DB session is mocked (fixture ORM objects, not persisted) — matches the
existing pure-unit-test convention in this suite (see test_coding_challenge_start.py).
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from persistence.models.core import User, Tenant, UserRole, TierEnum
from core.auth.dependencies import CurrentUser, can_host_coding_challenge
from core.user_management.schemas import UserUpdate
from core.user_management.service_async import UserManagementServiceAsync


def _user(role=UserRole.user, tier_override=None) -> User:
    now = datetime.now(timezone.utc)
    u = User(
        id=1, tenant_id=1, email="u@example.com", role=role, tier_override=tier_override,
        is_active=True, login_count=0, created_at=now, updated_at=now,
    )
    return u


def _tenant(tier=TierEnum.FREE) -> Tenant:
    return Tenant(id=1, name="Acme", slug="acme", tier=tier, is_active=True)


# ── CurrentUser.effective_tier ───────────────────────────────────────────────

def test_super_admin_effective_tier_is_enterprise_regardless_of_tenant_or_override():
    user = _user(role=UserRole.super_admin, tier_override=TierEnum.FREE)
    tenant = _tenant(tier=TierEnum.FREE)
    cu = CurrentUser(user=user, tenant=tenant)
    assert cu.effective_tier == TierEnum.ENTERPRISE
    assert cu.tier == "enterprise"


def test_override_wins_over_tenant_tier_for_regular_user():
    user = _user(role=UserRole.user, tier_override=TierEnum.CODING_CHALLENGE_PRO)
    tenant = _tenant(tier=TierEnum.FREE)
    cu = CurrentUser(user=user, tenant=tenant)
    assert cu.effective_tier == TierEnum.CODING_CHALLENGE_PRO


def test_no_override_falls_back_to_tenant_tier():
    user = _user(role=UserRole.user, tier_override=None)
    tenant = _tenant(tier=TierEnum.PRO)
    cu = CurrentUser(user=user, tenant=tenant)
    assert cu.effective_tier == TierEnum.PRO


# ── can_host_coding_challenge ─────────────────────────────────────────────────

def test_can_host_coding_challenge_true_for_super_admin():
    cu = CurrentUser(user=_user(role=UserRole.super_admin), tenant=_tenant(tier=TierEnum.FREE))
    assert can_host_coding_challenge(cu) is True


def test_can_host_coding_challenge_true_for_override_user():
    cu = CurrentUser(user=_user(tier_override=TierEnum.CODING_CHALLENGE_PRO), tenant=_tenant(tier=TierEnum.FREE))
    assert can_host_coding_challenge(cu) is True


def test_can_host_coding_challenge_false_otherwise():
    cu = CurrentUser(user=_user(), tenant=_tenant(tier=TierEnum.ENTERPRISE))
    assert can_host_coding_challenge(cu) is False


# ── Coding-challenge creation gate ───────────────────────────────────────────

def test_create_default_coding_challenge_rejects_ungated_user():
    from features.quiz.quiz_service_async import QuizBuilderServiceAsync
    cu = CurrentUser(user=_user(), tenant=_tenant(tier=TierEnum.FREE))
    service = QuizBuilderServiceAsync(tier_service=MagicMock())
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.create_default_coding_challenge(db, cu))
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "upgrade_required"
    db.execute.assert_not_called()


class _PastTheGateMarker(Exception):
    """Raised by a stubbed db.execute to prove control flow reached the DB
    layer, i.e. the can_host_coding_challenge() gate did not block it."""


def _assert_passes_gate(coro):
    """Run coro (which will hit our db.execute stub past the gate) and assert
    it raised the marker rather than the 403 upgrade_required HTTPException."""
    with pytest.raises(_PastTheGateMarker):
        asyncio.run(coro)


def test_create_default_coding_challenge_allows_override_user():
    from features.quiz.quiz_service_async import QuizBuilderServiceAsync
    cu = CurrentUser(user=_user(tier_override=TierEnum.CODING_CHALLENGE_PRO), tenant=_tenant(tier=TierEnum.FREE))
    service = QuizBuilderServiceAsync(tier_service=MagicMock())
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=_PastTheGateMarker())
    _assert_passes_gate(service.create_default_coding_challenge(db, cu))


def test_create_default_coding_challenge_allows_super_admin():
    from features.quiz.quiz_service_async import QuizBuilderServiceAsync
    cu = CurrentUser(user=_user(role=UserRole.super_admin), tenant=_tenant(tier=TierEnum.FREE))
    service = QuizBuilderServiceAsync(tier_service=MagicMock())
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=_PastTheGateMarker())
    _assert_passes_gate(service.create_default_coding_challenge(db, cu))


# ── update_user: tier_override admin API ─────────────────────────────────────

def _mock_db_for_update_user(target_user):
    db = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = target_user
    db.execute = AsyncMock(return_value=fetch_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def test_update_user_rejects_tier_override_from_non_super_admin():
    target = _user(role=UserRole.user)
    target.id = 2
    admin = _user(role=UserRole.admin)
    admin.id = 1
    admin.tenant_id = target.tenant_id

    db = _mock_db_for_update_user(target)
    service = UserManagementServiceAsync(db)
    update = UserUpdate(tier_override=TierEnum.CODING_CHALLENGE_PRO)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.update_user(target.id, update, admin))
    assert exc_info.value.status_code == 403


def test_update_user_allows_super_admin_to_set_tier_override():
    target = _user(role=UserRole.user)
    target.id = 2
    super_admin = _user(role=UserRole.super_admin)
    super_admin.id = 1

    db = _mock_db_for_update_user(target)
    service = UserManagementServiceAsync(db)
    update = UserUpdate(tier_override=TierEnum.CODING_CHALLENGE_PRO)

    asyncio.run(service.update_user(target.id, update, super_admin))
    assert target.tier_override == TierEnum.CODING_CHALLENGE_PRO


def test_update_user_allows_super_admin_to_clear_tier_override():
    target = _user(role=UserRole.user, tier_override=TierEnum.CODING_CHALLENGE_PRO)
    target.id = 2
    super_admin = _user(role=UserRole.super_admin)
    super_admin.id = 1

    db = _mock_db_for_update_user(target)
    service = UserManagementServiceAsync(db)
    update = UserUpdate(tier_override=None)
    # tier_override must be explicitly present in the payload (not just
    # defaulted) to be treated as "clear it" rather than "leave untouched".
    assert "tier_override" in update.model_fields_set

    asyncio.run(service.update_user(target.id, update, super_admin))
    assert target.tier_override is None

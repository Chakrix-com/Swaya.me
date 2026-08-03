"""
Unit tests for provision_workspace_job — the background job /start schedules
instead of doing create_workspace/wait_for_app_ready/mint_session_url inline.
Moved here specifically because the old inline flow was a fully-synchronous
70-150s+ chain under concurrency that raced nginx's proxy_read_timeout, giving a
candidate a false failure for a workspace that actually succeeded moments later.
Mocked DB session, matching this repo's existing convention for other
AsyncSessionLocal-opening jobs (see test_reap_abandoned_workspace_* in
test_coding_challenge_service.py).
"""
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from features.coding_challenge import coding_challenge_service_async as svc
from persistence.models.quiz import CodeWorkspace, CodeWorkspaceStatus, Question


def _fixture_workspace(status=CodeWorkspaceStatus.PROVISIONING) -> CodeWorkspace:
    return CodeWorkspace(
        id=1, tenant_id=1, quiz_id=1, question_id=10, candidate_email="a@b.com",
        ide_type="code_server", coder_workspace_name="cc-1-10-abcd1234",
        status=status, created_at=datetime(2026, 1, 1, 0, 0, 0),
    )


def _mock_session(db):
    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=db)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_session_cls


def test_provision_success_marks_active_resets_created_at_and_schedules_lifetime_cap():
    """The candidate's time budget must anchor to when the workspace actually
    became usable, not to when the row was first inserted (at /start time, before
    provisioning even began) — otherwise slow/contended provisioning silently eats
    into their coding time."""
    workspace = _fixture_workspace()
    question = Question(id=10, quiz_id=1, git_repo_url="https://github.com/x/y")
    db = AsyncMock()
    db.get = AsyncMock(side_effect=[workspace, question])
    db.commit = AsyncMock()

    with patch("persistence.database_async.AsyncSessionLocal", _mock_session(db)), \
         patch.object(svc.coder_client, "create_workspace", AsyncMock()) as mock_create, \
         patch.object(svc.coder_client, "wait_for_app_ready", AsyncMock(return_value=True)), \
         patch.object(svc.coder_client, "mint_session_url",
                       AsyncMock(return_value=("https://sandbox/url", "tok-name"))), \
         patch.object(svc, "schedule_lifetime_cap_job") as mock_schedule:
        asyncio.run(svc.provision_workspace_job(1))

    mock_create.assert_called_once_with(
        "cc-1-10-abcd1234", svc.settings.coder.code_server_template_name, "https://github.com/x/y",
    )
    assert workspace.status == CodeWorkspaceStatus.ACTIVE
    assert workspace.workspace_url == "https://sandbox/url"
    assert workspace.coder_token_name == "tok-name"
    assert workspace.created_at > datetime(2026, 1, 1, 0, 0, 0)  # reset to "now", not the original insert time
    db.commit.assert_called_once()

    workspace_id, workspace_name, fire_at = mock_schedule.call_args[0]
    assert workspace_id == 1
    assert workspace_name == "cc-1-10-abcd1234"
    expected_deadline = workspace.created_at + svc.timedelta(
        seconds=svc.settings.coder.workspace_max_lifetime_seconds
    )
    assert fire_at == expected_deadline


def test_provision_tolerates_wait_for_app_ready_timeout():
    """wait_for_app_ready returning False (not confirmed ready in time) must not
    be treated as fatal — only an actual create_workspace exception is. Matches
    the old inline /start flow's tolerance for this exact case."""
    workspace = _fixture_workspace()
    question = Question(id=10, quiz_id=1, git_repo_url="https://github.com/x/y")
    db = AsyncMock()
    db.get = AsyncMock(side_effect=[workspace, question])
    db.commit = AsyncMock()

    with patch("persistence.database_async.AsyncSessionLocal", _mock_session(db)), \
         patch.object(svc.coder_client, "create_workspace", AsyncMock()), \
         patch.object(svc.coder_client, "wait_for_app_ready", AsyncMock(return_value=False)), \
         patch.object(svc.coder_client, "mint_session_url",
                       AsyncMock(return_value=("https://sandbox/url", "tok-name"))), \
         patch.object(svc, "schedule_lifetime_cap_job"):
        asyncio.run(svc.provision_workspace_job(1))

    assert workspace.status == CodeWorkspaceStatus.ACTIVE  # still succeeds, just logs a warning


def test_provision_failure_marks_provision_failed_no_lifetime_cap_scheduled():
    workspace = _fixture_workspace()
    question = Question(id=10, quiz_id=1, git_repo_url="https://github.com/x/y")
    db = AsyncMock()
    db.get = AsyncMock(side_effect=[workspace, question])
    db.commit = AsyncMock()

    with patch("persistence.database_async.AsyncSessionLocal", _mock_session(db)), \
         patch.object(svc.coder_client, "create_workspace",
                       AsyncMock(side_effect=svc.coder_client.CoderClientError("boom", 1, "stderr"))), \
         patch.object(svc.coder_client, "wait_for_app_ready", AsyncMock()) as mock_wait, \
         patch.object(svc.coder_client, "mint_session_url", AsyncMock()) as mock_mint, \
         patch.object(svc, "schedule_lifetime_cap_job") as mock_schedule:
        asyncio.run(svc.provision_workspace_job(1))

    mock_wait.assert_not_called()  # never reached — create_workspace failed first
    mock_mint.assert_not_called()
    mock_schedule.assert_not_called()
    assert workspace.status == CodeWorkspaceStatus.PROVISION_FAILED
    assert workspace.workspace_url is None
    db.commit.assert_called_once()


def test_provision_noop_if_workspace_not_found():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    with patch("persistence.database_async.AsyncSessionLocal", _mock_session(db)), \
         patch.object(svc.coder_client, "create_workspace", AsyncMock()) as mock_create:
        asyncio.run(svc.provision_workspace_job(999))  # must not raise

    mock_create.assert_not_called()


def test_provision_noop_if_workspace_no_longer_provisioning():
    """A stale/duplicate job fire (e.g. reconcile_on_startup already marked this
    provision_failed after a restart) must not clobber whatever state it's
    actually in."""
    workspace = _fixture_workspace(status=CodeWorkspaceStatus.PROVISION_FAILED)
    db = AsyncMock()
    db.get = AsyncMock(return_value=workspace)

    with patch("persistence.database_async.AsyncSessionLocal", _mock_session(db)), \
         patch.object(svc.coder_client, "create_workspace", AsyncMock()) as mock_create:
        asyncio.run(svc.provision_workspace_job(1))

    mock_create.assert_not_called()
    assert workspace.status == CodeWorkspaceStatus.PROVISION_FAILED  # unchanged

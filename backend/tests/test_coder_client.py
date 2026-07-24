"""
Unit tests for features.coding_challenge.coder_client.
No real `coder` CLI calls — asyncio.create_subprocess_exec is mocked throughout.
"""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from features.coding_challenge import coder_client
from features.coding_challenge.coder_client import CoderClientError


def _mock_proc(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    proc.kill = lambda: None
    proc.wait = AsyncMock(return_value=None)
    return proc


def _patch_subprocess(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
    return patch(
        "asyncio.create_subprocess_exec",
        AsyncMock(return_value=_mock_proc(stdout, stderr, returncode)),
    )


# ── create_workspace / delete_workspace ─────────────────────────────────────

def test_create_workspace_calls_expected_args():
    with _patch_subprocess() as mock_exec:
        asyncio.run(coder_client.create_workspace("ws-1", "code-server-multi", "https://github.com/x/y"))
    args, kwargs = mock_exec.call_args
    assert args == (
        "coder", "create", "ws-1", "-t", "code-server-multi",
        "--parameter", "git_repo_url=https://github.com/x/y", "-y",
    )


def test_create_workspace_raises_on_nonzero_exit():
    with _patch_subprocess(stderr=b"boom", returncode=1):
        with pytest.raises(CoderClientError) as exc_info:
            asyncio.run(coder_client.create_workspace("ws-1", "tmpl", "https://x"))
    assert exc_info.value.returncode == 1
    assert "boom" in exc_info.value.stderr


def test_delete_workspace_calls_expected_args():
    with _patch_subprocess() as mock_exec:
        asyncio.run(coder_client.delete_workspace("ws-1"))
    args, _ = mock_exec.call_args
    assert args == ("coder", "delete", "ws-1", "-y")


def test_delete_workspace_raises_on_failure():
    with _patch_subprocess(returncode=2):
        with pytest.raises(CoderClientError):
            asyncio.run(coder_client.delete_workspace("ws-1"))


# ── mint_session_url / revoke_token ─────────────────────────────────────────

def test_get_workspace_id_finds_matching_name():
    listing = json.dumps([
        {"name": "other-ws", "id": "id-other"},
        {"name": "ws-1", "id": "id-123"},
    ]).encode()
    with _patch_subprocess(stdout=listing):
        result = asyncio.run(coder_client.get_workspace_id("ws-1"))
    assert result == "id-123"


def test_get_workspace_id_raises_when_not_found():
    listing = json.dumps([{"name": "other-ws", "id": "id-other"}]).encode()
    with _patch_subprocess(stdout=listing):
        with pytest.raises(CoderClientError):
            asyncio.run(coder_client.get_workspace_id("ws-missing"))


def test_mint_session_url_scopes_token_to_workspace_not_user():
    """Confirms the spike #2 correction: no `-u <email>`, scoped via --allow instead."""
    listing = json.dumps([{"name": "ws-1", "id": "id-123"}]).encode()

    call_args_list = []

    async def fake_exec(*args, **kwargs):
        call_args_list.append(args)
        if args[1] == "list":
            return _mock_proc(stdout=listing)
        if args[1] == "tokens" and args[2] == "create":
            return _mock_proc(stdout=b"tok-abc123\n")
        raise AssertionError(f"unexpected call: {args}")

    with patch("asyncio.create_subprocess_exec", fake_exec):
        url, token_name = asyncio.run(coder_client.mint_session_url(
            "ws-1", "code_server", "https://sandbox.swaya.me", "swaya-backend-svc",
        ))

    token_call = call_args_list[1]
    assert "-u" not in token_call
    assert "--allow" in token_call
    assert "workspace:id-123" in token_call
    assert url == "https://sandbox.swaya.me/@swaya-backend-svc/ws-1/apps/code-server?coder_session_token=tok-abc123"
    assert token_name == "ws-1-session"


def test_revoke_token_calls_expected_args():
    with _patch_subprocess() as mock_exec:
        asyncio.run(coder_client.revoke_token("ws-1-session"))
    args, _ = mock_exec.call_args
    assert args == ("coder", "tokens", "rm", "ws-1-session", "-y")


# ── exec_in_workspace ────────────────────────────────────────────────────────

def test_exec_in_workspace_always_cds_to_project_first():
    with _patch_subprocess(stdout=b"hello\n") as mock_exec:
        stdout, stderr, rc = asyncio.run(coder_client.exec_in_workspace("ws-1", "pytest -q"))
    args, _ = mock_exec.call_args
    assert args == ("coder", "ssh", "ws-1", "--", "bash", "-lc", "cd ~/project && pytest -q")
    assert stdout == "hello\n"
    assert rc == 0


def test_exec_in_workspace_propagates_nonzero_exit_code():
    with _patch_subprocess(returncode=7):
        _, _, rc = asyncio.run(coder_client.exec_in_workspace("ws-1", "exit 7"))
    assert rc == 7


def test_exec_in_workspace_does_not_raise_on_nonzero_exit():
    """Unlike the other wrappers, a failing test_command is expected output, not an error."""
    with _patch_subprocess(returncode=1):
        _, _, rc = asyncio.run(coder_client.exec_in_workspace("ws-1", "pytest -q"))
    assert rc == 1


# ── write_file_to_workspace ──────────────────────────────────────────────────

def test_write_file_to_workspace_pipes_content_via_stdin_not_command_line():
    with _patch_subprocess() as mock_exec:
        asyncio.run(coder_client.write_file_to_workspace("ws-1", "test_hidden.py", "def test(): pass"))
    args, kwargs = mock_exec.call_args
    assert args[:5] == ("coder", "ssh", "ws-1", "--", "bash")
    script = args[6]
    assert "test_hidden.py" in script
    # the actual content never appears in the argv-visible command string
    assert "def test(): pass" not in script
    assert kwargs["stdin"] == asyncio.subprocess.PIPE


def test_write_file_to_workspace_relative_path_resolved_against_project_dir():
    with _patch_subprocess() as mock_exec:
        asyncio.run(coder_client.write_file_to_workspace("ws-1", "sub/dir/test_hidden.py", "x"))
    args, _ = mock_exec.call_args
    script = args[6]
    assert "~/project/sub/dir/test_hidden.py" in script


def test_write_file_to_workspace_quotes_remote_path():
    """A remote_path containing shell metacharacters must not break out of the command
    (it should land inside a single shlex-quoted token, not as bare shell syntax)."""
    import shlex as _shlex
    malicious_path = "a; rm -rf /.py"
    with _patch_subprocess() as mock_exec:
        asyncio.run(coder_client.write_file_to_workspace("ws-1", malicious_path, "x"))
    args, _ = mock_exec.call_args
    script = args[6]
    tokens = _shlex.split(script)
    full_path = f"~/project/{malicious_path}"
    # the whole malicious string must appear intact as (part of) a single shell token,
    # never split into separate tokens the way bare `; rm -rf /.py` would parse
    assert any(full_path in tok for tok in tokens)
    assert "rm" not in tokens
    assert "-rf" not in tokens


def test_write_file_to_workspace_raises_on_failure():
    with _patch_subprocess(stderr=b"no space left", returncode=1):
        with pytest.raises(CoderClientError):
            asyncio.run(coder_client.write_file_to_workspace("ws-1", "x.py", "content"))


# ── stop_workspace / start_workspace ────────────────────────────────────────

def test_stop_workspace_calls_expected_args():
    with _patch_subprocess() as mock_exec:
        asyncio.run(coder_client.stop_workspace("ws-1"))
    args, _ = mock_exec.call_args
    assert args == ("coder", "stop", "ws-1", "-y")


def test_start_workspace_calls_expected_args():
    with _patch_subprocess() as mock_exec:
        asyncio.run(coder_client.start_workspace("ws-1"))
    args, _ = mock_exec.call_args
    assert args == ("coder", "start", "ws-1", "-y")


def test_stop_workspace_raises_on_failure():
    with _patch_subprocess(returncode=1):
        with pytest.raises(CoderClientError):
            asyncio.run(coder_client.stop_workspace("ws-1"))


def test_start_workspace_raises_on_failure():
    with _patch_subprocess(returncode=1):
        with pytest.raises(CoderClientError):
            asyncio.run(coder_client.start_workspace("ws-1"))

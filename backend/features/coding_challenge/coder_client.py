"""
Coder CLI wrapper — every interaction with the Coder sandbox (sandbox.swaya.me) goes
through `coder` CLI subprocess calls, never raw HTTP. There is no REST "exec" endpoint
for running commands in a workspace (confirmed during design: the reconnectingpty
endpoint is a raw WebSocket PTY stream, not a structured exec call), so `coder ssh
<workspace> -- <cmd>` is the one reliable mechanism with faithful exit-code semantics.

All calls assume the CLI is already logged in as the swaya-backend-svc service
account (session cached in ~/.config/coderv2/, inherited by the backend's own
systemd service since it runs as the same OS user).
"""
import asyncio
import json
import logging
import shlex
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_CLI_PATH = "coder"
DEFAULT_WORKING_DIR = "~/project"


class CoderClientError(Exception):
    """Raised when a coder CLI subprocess call fails unexpectedly."""

    def __init__(self, message: str, returncode: Optional[int] = None, stderr: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


async def _run(*args: str, cli_path: str = DEFAULT_CLI_PATH, input_data: Optional[bytes] = None,
                timeout: Optional[float] = None) -> tuple[str, str, int]:
    """Run `coder <args...>` as a subprocess, never through a shell. Returns (stdout, stderr, returncode)."""
    proc = await asyncio.create_subprocess_exec(
        cli_path, *args,
        stdin=asyncio.subprocess.PIPE if input_data is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(input=input_data), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise CoderClientError(f"coder {' '.join(args)} timed out after {timeout}s")
    return stdout.decode(errors="replace"), stderr.decode(errors="replace"), proc.returncode


async def create_workspace(workspace_name: str, template_name: str, git_repo_url: str,
                            cli_path: str = DEFAULT_CLI_PATH) -> None:
    """
    `coder create <name> -t <template> --parameter git_repo_url=<url> -y`.
    Naming policy (deterministic from quiz_id/question_id/candidate_email) lives in the
    orchestration service, not here — this just takes an already-computed name.
    """
    _, stderr, rc = await _run(
        "create", workspace_name, "-t", template_name,
        "--parameter", f"git_repo_url={git_repo_url}", "-y",
        cli_path=cli_path,
    )
    if rc != 0:
        raise CoderClientError(f"create_workspace({workspace_name}) failed", rc, stderr)


async def delete_workspace(workspace_name: str, cli_path: str = DEFAULT_CLI_PATH) -> None:
    """`coder delete <ws> -y`."""
    _, stderr, rc = await _run("delete", workspace_name, "-y", cli_path=cli_path)
    if rc != 0:
        raise CoderClientError(f"delete_workspace({workspace_name}) failed", rc, stderr)


async def stop_workspace(workspace_name: str, cli_path: str = DEFAULT_CLI_PATH) -> None:
    """`coder stop <ws> -y` — full container stop, drops any live candidate connection."""
    _, stderr, rc = await _run("stop", workspace_name, "-y", cli_path=cli_path)
    if rc != 0:
        raise CoderClientError(f"stop_workspace({workspace_name}) failed", rc, stderr)


async def start_workspace(workspace_name: str, cli_path: str = DEFAULT_CLI_PATH) -> None:
    """`coder start <ws> -y` — recreates the container fresh."""
    _, stderr, rc = await _run("start", workspace_name, "-y", cli_path=cli_path)
    if rc != 0:
        raise CoderClientError(f"start_workspace({workspace_name}) failed", rc, stderr)


async def get_workspace_id(workspace_name: str, cli_path: str = DEFAULT_CLI_PATH) -> str:
    """
    Resolves a workspace's Coder-internal ID from its name, via `coder list -o json`.
    Needed by mint_session_url's `--allow workspace:<id>` scoping (the name alone
    isn't accepted there).
    """
    stdout, stderr, rc = await _run("list", "-o", "json", "--all", cli_path=cli_path)
    if rc != 0:
        raise CoderClientError(f"get_workspace_id({workspace_name}): coder list failed", rc, stderr)
    workspaces = json.loads(stdout)
    for ws in workspaces:
        if ws.get("name") == workspace_name:
            return ws["id"]
    raise CoderClientError(f"get_workspace_id({workspace_name}): not found in coder list")


async def mint_session_url(workspace_name: str, ide_type: str, coder_url: str,
                            owner_username: str, app_slug: str = "code-server",
                            lifetime: str = "6h", cli_path: str = DEFAULT_CLI_PATH) -> tuple[str, str]:
    """
    Mints a token scoped to just this workspace (`--allow workspace:<id>`) for the
    already-authenticated service account — NOT `-u <candidate_email>` (confirmed
    during spike #2 that requires an existing Coder user matching that identity,
    which candidates never have). Returns (session_url, token_name) — caller persists
    token_name on code_workspace.coder_token_name so it can be revoked later.

    URL shape: https://<coder_url>/@<owner_username>/<workspace>/apps/<app-slug>?coder_session_token=<token>
    """
    workspace_id = await get_workspace_id(workspace_name, cli_path=cli_path)
    token_name = f"{workspace_name}-session"
    stdout, stderr, rc = await _run(
        "tokens", "create", "--name", token_name, "--lifetime", lifetime,
        "--allow", f"workspace:{workspace_id}",
        cli_path=cli_path,
    )
    if rc != 0:
        raise CoderClientError(f"mint_session_url({workspace_name}): token creation failed", rc, stderr)
    token = stdout.strip()
    url = f"{coder_url}/@{owner_username}/{workspace_name}/apps/{app_slug}?coder_session_token={token}"
    return url, token_name


async def revoke_token(token_name: str, cli_path: str = DEFAULT_CLI_PATH) -> None:
    """`coder tokens rm <name> -y`. Note: this alone does not end an already-open
    candidate browser session — confirmed during spike #3/#4 — the caller must also
    stop_workspace()/start_workspace() to close that window durably."""
    _, stderr, rc = await _run("tokens", "rm", token_name, "-y", cli_path=cli_path)
    if rc != 0:
        raise CoderClientError(f"revoke_token({token_name}) failed", rc, stderr)


async def _exec_bash_lc(workspace_name: str, script: str, input_data: Optional[bytes] = None,
                         timeout: Optional[float] = None, cli_path: str = DEFAULT_CLI_PATH) -> tuple[str, str, int]:
    """
    Runs `bash -lc <script>` in a workspace via `coder ssh <ws> -- <combined>`.

    **Load-bearing detail, found via Phase 9's real end-to-end walkthrough**: `bash`,
    `-lc`, and `script` must be passed as ONE combined, self-quoted string — not as
    3 separate argv elements. `coder ssh <ws> -- a b c` does not preserve multiple
    trailing arguments as an argv array the way a local `exec()` would; passing
    `"bash", "-lc", script` separately silently truncates or mis-splits `script` at
    whitespace once it crosses the SSH exec boundary (confirmed empirically: even
    `bash -lc "echo hello"` as 3 args produced no output, while the identical
    command as one pre-quoted string worked correctly). Combining locally with
    `shlex.quote` before handing it to `coder` as a single trailing argument avoids
    this entirely.
    """
    combined = f"bash -lc {shlex.quote(script)}"
    return await _run("ssh", workspace_name, "--", combined,
                       input_data=input_data, cli_path=cli_path, timeout=timeout)


async def exec_in_workspace(workspace_name: str, command: str, timeout: Optional[float] = None,
                             cli_path: str = DEFAULT_CLI_PATH) -> tuple[str, str, int]:
    """
    `coder ssh <ws> -- bash -lc "cd ~/project && <command>"`. Always runs from the
    fixed clone path. `bash -lc` (login shell) is required for PATH correctness
    (confirmed during spikes: a plain non-login shell doesn't have ~/.local/bin,
    where the Claude Code installer places its binary, on PATH) even though
    CLAUDE_CODE_OAUTH_TOKEN itself is now a container-level env var so it doesn't
    depend on shell rc files at all.

    `command` is expected to be host-authored shell syntax (test_command, git
    subcommands, etc.) — it is intentionally NOT shell-escaped, since it's meant to
    be interpreted as a shell command. Untrusted large content (hidden test bodies)
    must go through write_file_to_workspace's stdin-piped path instead, never here.
    """
    script = f"cd {DEFAULT_WORKING_DIR} && {command}"
    return await _exec_bash_lc(workspace_name, script, cli_path=cli_path, timeout=timeout)


async def write_file_to_workspace(workspace_name: str, remote_path: str, content: str,
                                   cli_path: str = DEFAULT_CLI_PATH) -> None:
    """
    Writes `content` into `remote_path` (relative to ~/project unless absolute) via
    stdin, never string-interpolated into the command line — avoids injection and
    argument-length issues for potentially large content (hidden test bodies).
    `remote_path` itself IS shell-quoted when building the mkdir/cat command, since
    it's host-authored data landing inside a shell string.

    A relative path is resolved by `cd`-ing into `~/project` UNQUOTED first (so
    normal tilde expansion applies), then operating on the plain relative path —
    **found via Phase 9's real walkthrough**: embedding `~/project/...` directly
    inside a `shlex.quote()`'d string breaks tilde expansion entirely (quoting
    suppresses it, since expansion is a shell-parse-time behavior, not something
    `mkdir`/`cat` do on their own), silently creating a literal `~`-named directory
    instead of resolving to the home directory.
    """
    if remote_path.startswith("/"):
        quoted_path = shlex.quote(remote_path)
        script = f"mkdir -p $(dirname {quoted_path}) && cat > {quoted_path}"
    else:
        quoted_path = shlex.quote(remote_path)
        script = f"cd {DEFAULT_WORKING_DIR} && mkdir -p $(dirname {quoted_path}) && cat > {quoted_path}"
    _, stderr, rc = await _exec_bash_lc(workspace_name, script, input_data=content.encode(), cli_path=cli_path)
    if rc != 0:
        raise CoderClientError(f"write_file_to_workspace({workspace_name}, {remote_path}) failed", rc, stderr)

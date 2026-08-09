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

_provision_semaphore: Optional[asyncio.Semaphore] = None


def _get_provision_semaphore() -> asyncio.Semaphore:
    """Lazily-constructed module-level semaphore limiting concurrent `coder create`
    subprocesses (separate from MAX_CONCURRENT_WORKSPACES, which only rejects above
    a count — this actually queues). Built lazily, not at import time, since
    asyncio.Semaphore should be created inside a running event loop context."""
    global _provision_semaphore
    if _provision_semaphore is None:
        from core.config.settings import settings
        _provision_semaphore = asyncio.Semaphore(settings.coder.max_parallel_provisions)
    return _provision_semaphore


class CoderClientError(Exception):
    """Raised when a coder CLI subprocess call fails unexpectedly. Folds returncode/
    stderr into the exception's own message (not just attributes) — found via a real
    Phase 10 resilience test that every catch site across this feature logs/persists
    failures via plain `str(e)`/`%s`, which previously showed only the generic
    "<call> failed" text and silently dropped the actual CLI stderr/exit code that
    would explain why, including in the error_message an examiner sees on a failed
    CodeSubmission."""

    def __init__(self, message: str, returncode: Optional[int] = None, stderr: str = ""):
        full_message = message
        if stderr:
            full_message = f"{full_message}: {stderr.strip()}"
        if returncode is not None:
            full_message = f"{full_message} (rc={returncode})"
        super().__init__(full_message)
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

    Gated by a semaphore (CODER_MAX_PARALLEL_PROVISIONS) so concurrent provisioning
    requests queue rather than all firing `coder create` subprocesses against the
    same Coder/Terraform backend simultaneously — that contention is what caused
    provisioning time to vary so much under concurrency in the first place.
    """
    async with _get_provision_semaphore():
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
    """`coder tokens rm <name> --delete` — unlike every other coder subcommand this
    wrapper calls, `tokens remove` has no `-y` confirmation flag at all and errors
    out if passed one (found via Phase 9's real walkthrough: every revoke_token call
    was silently failing with a CLI argument-parsing error, tolerated by /submit's
    try/except but leaving every candidate token alive — this had already surfaced
    once during Phase 1's spike #3 testing too, but that finding wasn't carried
    into this implementation at the time).

    `--delete` is required, not optional: without it, `tokens remove` only expires
    the token but leaves its NAME permanently reserved (also found via Phase 9's
    walkthrough — a second /start attempt against the same deterministic
    workspace-derived token_name failed with "A token with name ... already
    exists" even after the first token had been "removed"). This project has no
    audit-trail need for these ephemeral per-session tokens, so a hard delete
    (freeing the name for the next mint_session_url call against the same
    workspace) is the correct choice here, not the softer expire-only default.

    Note: revoking alone does not end an already-open candidate browser session —
    confirmed during spike #3/#4 — the caller must also stop_workspace()/
    start_workspace() to close that window durably."""
    _, stderr, rc = await _run("tokens", "rm", token_name, "--delete", cli_path=cli_path)
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


async def wait_for_app_ready(workspace_name: str, port: int = 13337, timeout: float = 210.0,
                              cli_path: str = DEFAULT_CLI_PATH) -> bool:
    """`coder create` only waits for the agent to connect, not for the code-server
    registry module's own startup script to finish installing/launching code-server
    inside the container — handing the candidate a session URL before that's done
    causes a real "connection refused" 502 on their very first open (confirmed live
    at least three times now: during initial design, again on 2026-08-02, and again
    on 2026-08-09 against a real candidate — code-server startup measured taking
    ~145-150s in practice, sometimes more).

    Timeout raised from 120s to 210s on 2026-08-09 — the original 120s figure was
    sized against a constraint that no longer exists: this used to be called
    synchronously from within the `/start` HTTP request itself, so it had to stay
    under the frontend's LONG_TIMEOUT and this route's nginx proxy_read_timeout or
    the request would fail out from under it regardless of what this function did.
    Since the async-provisioning refactor (commit 3adbc49, "/start" now acks fast
    and does this work in provision_workspace_job, a background APScheduler job),
    nothing is blocked on this call anymore — the frontend just polls /status
    separately. There's no reason left to cut this off at 120s when the real
    startup time observed in practice runs right up against it; 210s gives ~60s of
    margin over the worst case actually measured, at the cost of the (rare) truly-
    stuck case waiting longer before falling through to the "proceed anyway" path
    below — an acceptable tradeoff now that nothing else times out because of it.

    Polls from inside the workspace until the port is actually accepting connections.
    Returns False (not True) on timeout — caller proceeds anyway rather than blocking
    provisioning indefinitely; this just makes the common case reliable, not a
    guarantee."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        try:
            _, _, rc = await exec_in_workspace(
                workspace_name, f"curl -sf -o /dev/null http://localhost:{port}",
                timeout=10.0, cli_path=cli_path,
            )
        except Exception:
            rc = 1
        if rc == 0:
            return True
        await asyncio.sleep(2)
    return False


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

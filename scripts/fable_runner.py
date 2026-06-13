#!/usr/bin/env python3
"""
fable_runner.py
Runs the Fable implementation plan through Claude Code.
Auto-waits on usage-limit hits and resumes the same session when the limit clears.

Usage (inside screen or tmux so SSH disconnect doesn't kill it):
    screen -S fable
    python3 /home/vinay/Swaya.me/scripts/fable_runner.py

Watch live from another terminal:
    tail -f /home/vinay/Swaya.me/logs/fable_runner.log

Grep for key events:
    grep -E "RUN #|LIMIT HIT|RESUMED|DONE|ERROR" /home/vinay/Swaya.me/logs/fable_runner.log
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
import time
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
PLAN_FILE     = "/home/vinay/Swaya.me/specs/fable-implementation-plan.md"
LOG_FILE      = "/home/vinay/Swaya.me/logs/fable_runner.log"
SESSION_FILE  = "/tmp/fable_session_id"
SESSIONS_DIR  = os.path.expanduser("~/.claude/projects/-home-vinay-Swaya-me/")
MAX_LOG_BYTES = 50 * 1_024 * 1_024  # 50 MB before rotation
FALLBACK_WAIT = 60 * 60             # 1 hour if reset time can't be parsed from error

INITIAL_PROMPT = (
    "Execute the implementation plan at "
    "/home/vinay/Swaya.me/specs/fable-implementation-plan.md. "
    "Work through every item in priority order starting from P0. "
    "Follow the Definition of Done in the file for each item. "
    "Update the Status column in the plan file as you complete each item."
)
RESUME_PROMPT = (
    "Continue executing the Fable implementation plan from where you left off. "
    "Check the Status column in fable-implementation-plan.md to see what's done and pick up the next item."
)

# ── Patterns ──────────────────────────────────────────────────────────────────
LIMIT_RE = re.compile(
    r"usage.?limit|rate.?limit|too many requests|quota.?exceeded|limit.?reached|429",
    re.IGNORECASE,
)
RETRY_AFTER_RE = re.compile(r"retry.?after[:\s]+(\d+)\s*seconds?", re.IGNORECASE)
RESET_AT_RE = re.compile(
    r"resets?\s+(?:at|on)\s+(.+?)(?:[.,\n]|$)"
    r"|available\s+again\s+(?:at|on)\s+(.+?)(?:[.,\n]|$)"
    r"|(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})",
    re.IGNORECASE,
)

# ── Logging ───────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
_log_fh = open(LOG_FILE, "a", buffering=1)


def log(msg: str, raw: bool = False) -> None:
    """Write timestamped line to both terminal and log file. raw=True skips timestamp."""
    global _log_fh
    line = msg if raw else f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    if _log_fh.tell() > MAX_LOG_BYTES:
        _log_fh.close()
        os.rename(LOG_FILE, LOG_FILE + ".1")
        _log_fh = open(LOG_FILE, "a", buffering=1)
        log("LOG ROTATED — continued in new file")
    _log_fh.write(line + "\n")


# ── Session ID ────────────────────────────────────────────────────────────────
def _session_files() -> list[str]:
    return glob.glob(os.path.join(SESSIONS_DIR, "*.jsonl"))


def grab_new_session_id(pre_mtime: float) -> str | None:
    """Return ID of a session .jsonl created after pre_mtime, or None."""
    new = [f for f in _session_files() if os.path.getmtime(f) > pre_mtime]
    if not new:
        return None
    newest = max(new, key=os.path.getmtime)
    return os.path.splitext(os.path.basename(newest))[0]


def save_session(sid: str) -> None:
    with open(SESSION_FILE, "w") as f:
        f.write(sid)


def load_session() -> str | None:
    if os.path.exists(SESSION_FILE):
        val = open(SESSION_FILE).read().strip()
        return val or None
    return None


def clear_session() -> None:
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)


# ── Reset-time parsing ────────────────────────────────────────────────────────
def parse_reset_secs(text: str) -> int | None:
    """Try to extract seconds-until-reset from limit error text. Returns None if unparseable."""
    m = RETRY_AFTER_RE.search(text)
    if m:
        return int(m.group(1)) + 60  # +60s buffer

    m = RESET_AT_RE.search(text)
    if m:
        raw = next((g for g in m.groups() if g), None)
        if raw:
            try:
                dt = datetime.fromisoformat(raw.strip().replace(" ", "T"))
                delta = int((dt - datetime.now()).total_seconds()) + 60
                return max(delta, 60)
            except ValueError:
                log(f"Could not parse reset timestamp: {raw!r}")
    return None


# ── Core runner ───────────────────────────────────────────────────────────────
def run_claude(prompt: str, session_id: str | None, run_num: int) -> tuple[bool, int | None, str | None]:
    """
    Launch claude, stream all output to terminal + log.
    Returns (limit_hit, reset_secs, session_id).
    """
    if session_id:
        cmd = ["claude", "--dangerously-skip-permissions", "--resume", session_id, "-p", prompt]
    else:
        cmd = ["claude", "--dangerously-skip-permissions", "-p", prompt]

    log("=" * 64)
    log(f"RUN #{run_num}  |  session: {'new' if not session_id else session_id[:12] + '...'}")
    log(f"PROMPT: {prompt[:120]}{'...' if len(prompt) > 120 else ''}")
    log("=" * 64)

    # Snapshot max mtime before launch so we can detect the new session file
    existing = _session_files()
    pre_mtime = max((os.path.getmtime(f) for f in existing), default=0.0)

    captured: list[str] = []
    limit_hit = False
    reset_secs = None
    sid = session_id

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # merge stderr so we catch everything
            text=True,
            bufsize=1,
            cwd="/home/vinay/Swaya.me",
        )
    except FileNotFoundError:
        log("ERROR: 'claude' command not found — is Claude Code installed and in PATH?")
        sys.exit(1)

    # Give the process 3 seconds to create its session file, then capture the ID
    time.sleep(3)
    if not sid:
        new_sid = grab_new_session_id(pre_mtime)
        if new_sid:
            sid = new_sid
            save_session(sid)
            log(f"SESSION ID: {sid}")
        else:
            log("WARNING: session ID not detected — automatic resume will not be possible if limit hits")

    try:
        for line in proc.stdout:
            stripped = line.rstrip()
            log(stripped, raw=True)
            captured.append(stripped)
            if LIMIT_RE.search(stripped):
                limit_hit = True

        proc.wait()

    except KeyboardInterrupt:
        log("Interrupted by user — stopping runner.")
        proc.terminate()
        sys.exit(0)

    if limit_hit:
        reset_secs = parse_reset_secs("\n".join(captured))
        log(f"RUN #{run_num} — LIMIT HIT (exit code {proc.returncode})")
    else:
        log(f"RUN #{run_num} — COMPLETE (exit code {proc.returncode})")

    return limit_hit, reset_secs, sid


# ── Log viewer ────────────────────────────────────────────────────────────────
def open_log_viewer() -> None:
    """
    Open a second window/pane that tails the log file so it's always on screen.
    - Inside screen: opens a new window named 'fable-log' (switch with Ctrl+A, n)
    - Inside tmux:   splits vertically, right pane tails the log (navigate with Ctrl+B, arrow)
    - Neither:       prints a tip to tail manually
    """
    if os.environ.get("STY"):  # running inside GNU screen
        subprocess.Popen(
            ["screen", "-X", "screen", "-t", "fable-log", "tail", "-f", LOG_FILE]
        )
        log("LOG VIEWER: opened 'fable-log' screen window — switch with Ctrl+A, n")
    elif os.environ.get("TMUX"):  # running inside tmux
        subprocess.Popen(
            ["tmux", "split-window", "-h", f"tail -f {LOG_FILE}"]
        )
        log("LOG VIEWER: opened log pane (right half) — navigate with Ctrl+B, arrow keys")
    else:
        log(f"LOG VIEWER TIP: in another terminal run:  tail -f {LOG_FILE}")


# ── Main loop ─────────────────────────────────────────────────────────────────
def main() -> None:
    log("=" * 64)
    log("FABLE RUNNER STARTED")
    log(f"Plan file: {PLAN_FILE}")
    log(f"Log file:  {LOG_FILE}")
    log("=" * 64)
    open_log_viewer()

    session_id = load_session()
    if session_id:
        log(f"Resuming existing session: {session_id}")
        prompt = RESUME_PROMPT
    else:
        log("No existing session found — starting fresh")
        prompt = INITIAL_PROMPT

    run_num = 0
    while True:
        run_num += 1
        limit_hit, reset_secs, session_id = run_claude(prompt, session_id, run_num)

        if not limit_hit:
            log("FABLE RUNNER DONE — plan execution finished.")
            clear_session()
            break

        # After a limit hit, always use the resume prompt for subsequent runs
        prompt = RESUME_PROMPT

        wait = reset_secs if reset_secs else FALLBACK_WAIT
        source = "from error message" if reset_secs else "fallback 1-hour wait"
        wake_at = datetime.fromtimestamp(time.time() + wait)
        log(f"LIMIT WAIT: sleeping {wait}s ({source}) — will resume at {wake_at.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            time.sleep(wait)
        except KeyboardInterrupt:
            log("Interrupted during wait — stopping runner. Run again to resume.")
            sys.exit(0)

        log(f"RESUMING after wait — session: {session_id}")


if __name__ == "__main__":
    main()

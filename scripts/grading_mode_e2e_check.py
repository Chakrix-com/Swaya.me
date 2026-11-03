"""
Real end-to-end check for the grading-mode selector (2026-08-09), T34 of
_private/coding_challenge_grading_mode_tasks_20260809.md.

Provisions one real candidate workspace on test.swaya.me (same invite->OTP->
start pattern as coder_submit_extension_check.py), writes real code + a
synthetic transcript directly into it, fires /submit, and lets the real
run_grading_job pipeline run end to end in Deterministic mode — the one
piece that hadn't yet been proven working together in a live run (Phase 3's
Docker-image ruff/lizard install + Phase 4's harvest/dispatch wiring, each
verified separately but never through one real submission before this).

Then confirms the "byte-identical regrade" claim directly: calls
_run_ai_scoring twice against the SAME real submission row (bypassing
regrade_submission's PARTIAL_FAILED-only status gate, since a GRADED
submission can't go through the real regrade endpoint — this is exactly why
the plan's Verification section calls for a direct scratch-script call
instead).

TEST ONLY — never point SWAYA_API_BASE at www.swaya.me. Never mutates real
production data (matches this session's established discipline).

Usage:
    TOKEN=$(cd backend && source .venv/bin/activate && \\
        python /home/vinay/Swaya.me/scripts/generate_selenium_token.py meetnishant@gmail.com)
    SWAYA_API_BASE=https://test.swaya.me/api/v1 SWAYA_TOKEN="$TOKEN" \\
        python scripts/grading_mode_e2e_check.py
"""
import base64
import json
import os
import subprocess
import sys
import time

import redis
import requests

BASE = os.environ.get("SWAYA_API_BASE", "https://test.swaya.me/api/v1")
TOKEN = os.environ.get("SWAYA_TOKEN", "").strip()

if "www.swaya.me" in BASE:
    print("FATAL: refusing to run against www.swaya.me — provisions a real Coder workspace.")
    sys.exit(1)
if not TOKEN:
    print("FATAL: SWAYA_TOKEN env var not set")
    sys.exit(1)

H = {"Authorization": f"Bearer {TOKEN}"}
r_client = redis.Redis(host="localhost", port=6379, db=0)

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
INFO = "\033[94m INFO\033[0m"
issues = []


def check(name, condition):
    print(f"{PASS if condition else FAIL} {name}")
    if not condition:
        issues.append(name)
    return condition


def decode_jwt_payload(token):
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def coder_ssh(workspace_name, cmd, timeout=30, input_data=None):
    combined = f"bash -lc {json.dumps(cmd)}"
    proc = subprocess.run(["coder", "ssh", workspace_name, "--", combined],
                           capture_output=True, text=True, timeout=timeout, input=input_data)
    return proc.stdout, proc.stderr, proc.returncode


TRANSCRIPT_ENTRIES = [
    {"type": "user", "timestamp": "2026-08-09T08:00:00.000Z", "origin": {"kind": "human"},
     "message": {"role": "user", "content": [{"type": "text",
        "text": "Implement two functions in bank.py: `add(a, b)` that returns a+b, and "
                "`messy(a,b,c,d)` with deeply nested if statements checking each argument, "
                "matching the test_bank.py hidden test expectations for edge cases."}]}},
    {"type": "assistant", "timestamp": "2026-08-09T08:00:30.000Z",
     "message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": "pytest -q"}}]}},
]


def main():
    s = requests.Session()
    s.headers.update(H)

    print(f"Target: {BASE}\n")

    title = f"grading-mode-e2e-{int(time.time())}"
    r = s.post(f"{BASE}/quizzes/", json={"title": title, "quiz_type": "coding_challenge"})
    if r.status_code not in (200, 201):
        print(f"FATAL: create quiz failed: {r.status_code} {r.text[:300]}")
        sys.exit(1)
    quiz_id = r.json()["id"]
    print(f"{INFO} Created quiz {quiz_id}")

    r = s.post(f"{BASE}/quizzes/{quiz_id}/questions", json={
        "question_type": "coding_challenge",
        "text": "Implement add() and messy() in bank.py",
        "git_repo_url": "https://github.com/octocat/Hello-World",
        "test_command": "pytest",
        "grading_mode": "deterministic",
    })
    if r.status_code not in (200, 201):
        print(f"FATAL: create question failed: {r.status_code} {r.text[:300]}")
        s.delete(f"{BASE}/quizzes/{quiz_id}")
        sys.exit(1)
    question_id = r.json()["id"]
    check("question created with grading_mode=deterministic", r.json().get("grading_mode") == "deterministic")
    print(f"{INFO} Created question {question_id}")

    email = f"grading-mode-e2e-{int(time.time())}@example.com"
    r = s.post(f"{BASE}/quizzes/{quiz_id}/coding-challenge/invite", json={"candidate_emails": [email]})
    if r.status_code != 200:
        print(f"FATAL: invite failed: {r.status_code} {r.text[:300]}")
        s.delete(f"{BASE}/quizzes/{quiz_id}")
        sys.exit(1)
    invite_url = r.json()[0]["invite_url"]
    token = invite_url.rsplit("/", 1)[-1]
    payload = decode_jwt_payload(token)
    jti = payload["jti"]

    anon = requests.Session()
    r = anon.post(f"{BASE}/coding-challenge/{token}/request-otp")
    check("request-otp succeeds", r.status_code == 200)
    otp_key = f"coding_challenge_otp:{jti}:{email.lower()}"
    raw = r_client.get(otp_key)
    otp = json.loads(raw)["otp"]

    print(f"{INFO} Firing /start...")
    r = anon.post(f"{BASE}/coding-challenge/{token}/start",
                   json={"ide_type": "code_server", "otp": otp}, timeout=30)
    if not check("/start returns 200", r.status_code == 200):
        print(f"  body: {r.text[:300]}")
        s.delete(f"{BASE}/quizzes/{quiz_id}")
        sys.exit(1)

    workspace_url = None
    t0 = time.time()
    while time.time() - t0 < 180:
        r = anon.get(f"{BASE}/coding-challenge/{token}/status", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "provision_failed":
                check("provisioning succeeded", False)
                s.delete(f"{BASE}/quizzes/{quiz_id}")
                sys.exit(1)
            if data.get("workspace_url"):
                workspace_url = data["workspace_url"]
                break
        time.sleep(2)
    check("workspace became ready within 180s", workspace_url is not None)
    if not workspace_url:
        s.delete(f"{BASE}/quizzes/{quiz_id}")
        sys.exit(1)

    import hashlib
    workspace_name = f"cc-{quiz_id}-{question_id}-" + hashlib.sha256(f"{email.lower()}:1".encode()).hexdigest()[:8]
    print(f"{INFO} Workspace ready: {workspace_name}")

    # ── Write real code: one clean function, one deliberately messy one —
    # same fixture shape as the manual T20 verification, now exercised
    # through the real harvest pipeline instead of a standalone check. ──
    code = (
        "def add(a, b):\n    return a + b\n\n\n"
        "def messy(a, b, c, d):\n"
        "    if a:\n        if b:\n            if c:\n                if d:\n                    return 1\n"
        "    return 0\n"
    )
    stdout, stderr, rc = coder_ssh(workspace_name, "cat > /home/coder/project/bank.py", input_data=code)
    check("wrote bank.py into the workspace", rc == 0)

    # Real AI-authored + candidate commits, so validation_discipline/
    # ai_usage_efficiency have real signal too, not just code_quality/architecture.
    commit_script = (
        "cd /home/coder/project && git add bank.py && "
        "GIT_AUTHOR_NAME='Claude Code' GIT_AUTHOR_EMAIL='ai@swaya.local' "
        "GIT_COMMITTER_NAME='Claude Code' GIT_COMMITTER_EMAIL='ai@swaya.local' "
        "git commit -m 'ai-edit: add bank.py' && "
        "pytest -q || true"
    )
    stdout, stderr, rc = coder_ssh(workspace_name, commit_script)
    check("committed bank.py as ai@swaya.local", rc == 0)

    # Synthetic transcript at the real harvest path (~/.claude/projects/*/*.jsonl)
    # so _extract_candidate_prompts/_compute_ai_usage_efficiency have real input.
    transcript_lines = "\n".join(json.dumps(e) for e in TRANSCRIPT_ENTRIES)
    mkdir_script = "mkdir -p /home/coder/.claude/projects/e2e-check && cat > /home/coder/.claude/projects/e2e-check/session.jsonl"
    stdout, stderr, rc = coder_ssh(workspace_name, mkdir_script, input_data=transcript_lines)
    check("wrote synthetic transcript", rc == 0)

    print(f"{INFO} Firing /submit...")
    r = anon.post(f"{BASE}/coding-challenge/{token}/submit", timeout=30)
    check("/submit returns 200", r.status_code == 200)

    print(f"{INFO} Polling for grading completion (up to 4 min)...")
    submission_id = None
    t0 = time.time()
    final_status = None
    while time.time() - t0 < 240:
        r = s.get(f"{BASE}/quiz-builder/questions/{question_id}/coding-challenge-review", timeout=10)
        if r.status_code == 200:
            entries = r.json().get("candidates", [])
            for entry in entries:
                sub = (entry.get("submission") or {})
                if sub.get("status") in ("graded", "partial_failed", "failed"):
                    submission_id = sub.get("id")
                    final_status = sub.get("status")
                    break
        if final_status:
            break
        time.sleep(5)

    check(f"grading reached a terminal status within 4 min (got: {final_status})", final_status is not None)
    if not submission_id:
        print(f"{FAIL} Could not find submission id — dumping raw review response for debugging")
        print(r.text[:1000] if r.status_code == 200 else f"status {r.status_code}")
        s.delete(f"{BASE}/quizzes/{quiz_id}")
        sys.exit(1)

    print(f"{INFO} submission_id={submission_id}, status={final_status}")

    # ── Inspect the real DB row directly ──
    sys.path.insert(0, "/home/vinay/Swaya.me/backend")
    os.environ.setdefault("PYTHONPATH", "/home/vinay/Swaya.me/backend")
    # Real bug hit running this the first time: importing persistence.database_async
    # triggers Settings() validation, which needs JWT_SECRET etc from .env — this
    # script's own process never loads it (unlike generate_selenium_token.py, which
    # does explicitly). Must load before any backend import below.
    from dotenv import load_dotenv
    load_dotenv("/home/vinay/Swaya.me/backend/.env", override=True)
    import pymysql
    # Credentials come from the test backend .env loaded above (repo is public).
    conn = pymysql.connect(host="127.0.0.1", port=3306, user=os.environ["DB_USER"],
                            password=os.environ["DB_PASSWORD"], database="swayame_test")
    cur = conn.cursor()
    cur.execute(
        "SELECT status, grading_mode_used, static_analysis_result, score_breakdown, ai_score "
        "FROM code_submissions WHERE id=%s", (submission_id,),
    )
    row = cur.fetchone()
    status, grading_mode_used, static_analysis_result_raw, score_breakdown_raw, ai_score = row
    static_analysis_result = json.loads(static_analysis_result_raw) if static_analysis_result_raw else None
    score_breakdown = json.loads(score_breakdown_raw) if score_breakdown_raw else None

    check("submission graded successfully", status == "graded")
    check("grading_mode_used == deterministic", grading_mode_used == "deterministic")
    check("static_analysis_result is real (not the punitive fallback)",
          static_analysis_result is not None and static_analysis_result.get("failed") is False)
    if static_analysis_result:
        print(f"{INFO} Real harvested static_analysis_result: {static_analysis_result}")
    check("code_quality score reflects real analysis, not the fallback 28",
          score_breakdown and score_breakdown.get("code_quality", {}).get("score") != 28)
    if score_breakdown:
        print(f"{INFO} score_breakdown: {json.dumps(score_breakdown, indent=2)}")
    print(f"{INFO} ai_score: {ai_score}")

    # ── Byte-identical regrade check — direct function call, bypassing
    # regrade_submission's PARTIAL_FAILED-only gate (plan Verification #3). ──
    from persistence.database_async import AsyncSessionLocal
    from persistence.models.quiz import CodeSubmission, CodeWorkspace, Question
    from features.coding_challenge import grading_service_async as gsvc
    import asyncio

    async def rescore_and_compare():
        async with AsyncSessionLocal() as db:
            submission = await db.get(CodeSubmission, submission_id)
            workspace = await db.get(CodeWorkspace, submission.workspace_id)
            question = await db.get(Question, submission.question_id)
            first_breakdown = dict(submission.score_breakdown)
            await gsvc._run_ai_scoring(db, submission, workspace, question)
            second_breakdown = submission.score_breakdown
            return first_breakdown, second_breakdown

    first_bd, second_bd = asyncio.run(rescore_and_compare())
    check("re-scoring the same submission gives byte-identical score_breakdown (Deterministic mode)",
          first_bd == second_bd)
    if first_bd != second_bd:
        print(f"{INFO} first:  {json.dumps(first_bd, indent=2)}")
        print(f"{INFO} second: {json.dumps(second_bd, indent=2)}")

    print(f"\n{'='*60}")
    if issues:
        print(f"{FAIL} {len(issues)} issue(s): {issues}")
    else:
        print(f"{PASS} All checks passed")

    print(f"{INFO} Leaving quiz {quiz_id} / question {question_id} in place for manual inspection if needed.")
    print(f"{INFO} Clean up later with: DELETE FROM quizzes WHERE id={quiz_id} (cascades)")


if __name__ == "__main__":
    main()

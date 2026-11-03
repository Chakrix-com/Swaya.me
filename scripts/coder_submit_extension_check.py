"""
Real end-to-end check for the swaya-submit-timer VS Code extension's data
plumbing (Phase 1, T09 of coder_submit_extension_tasks_20260809.md) and,
optionally, a live scratch workspace to manually install the extension into
for Phase 4 testing.

Creates one real candidate (quiz + coding_challenge question + invite + OTP,
via the actual invite->OTP->start flow — same pattern as
coding_challenge_concurrency_check.py), fires a real /start, polls /status
until the workspace is ready, then `coder ssh`'s in directly to inspect
/home/coder/.swaya/session.json: existence, permissions (600), and that its
fields decode to the right candidate/quiz/question and a sane createdAt/
timeBudgetSeconds.

Deliberately sets a SHORT time_budget_seconds (default 300s = 5 minutes) so
the same workspace can be reused afterwards to observe the countdown's
60s->1s interval switch (under 5 min) and auto-submit-at-zero behavior
without waiting hours.

TEST ONLY — never point SWAYA_API_BASE at www.swaya.me; this provisions a
real Coder workspace on the shared sandbox.

Usage:
    TOKEN=$(cd backend && source .venv/bin/activate && \\
        python /home/vinay/Swaya.me/scripts/generate_selenium_token.py meetnishant@gmail.com)
    SWAYA_API_BASE=https://test.swaya.me/api/v1 SWAYA_TOKEN="$TOKEN" \\
        python scripts/coder_submit_extension_check.py [--keep] [--budget-seconds N]
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
KEEP = "--keep" in sys.argv
BUDGET_SECONDS = 300
for i, a in enumerate(sys.argv):
    if a == "--budget-seconds" and i + 1 < len(sys.argv):
        BUDGET_SECONDS = int(sys.argv[i + 1])

if "www.swaya.me" in BASE:
    print("FATAL: refusing to run against www.swaya.me — this provisions a real Coder")
    print("       workspace on the shared sandbox. Run against test.swaya.me only.")
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


def coder_ssh(workspace_name, cmd, timeout=30):
    """Mirrors coder_client._exec_bash_lc's one-combined-string requirement —
    coder ssh <ws> -- a b c does NOT preserve multiple trailing args as argv."""
    combined = f"bash -lc {json.dumps(cmd)}"
    proc = subprocess.run(["coder", "ssh", workspace_name, "--", combined],
                           capture_output=True, text=True, timeout=timeout)
    return proc.stdout, proc.stderr, proc.returncode


def main():
    s = requests.Session()
    s.headers.update(H)

    print(f"Target: {BASE}  |  time_budget_seconds={BUDGET_SECONDS}\n")

    title = f"submit-ext-check-{int(time.time())}"
    r = s.post(f"{BASE}/quizzes/", json={"title": title, "quiz_type": "coding_challenge"})
    if r.status_code not in (200, 201):
        print(f"FATAL: create quiz failed: {r.status_code} {r.text[:300]}")
        sys.exit(1)
    quiz_id = r.json()["id"]
    print(f"{INFO} Created quiz {quiz_id}")

    r = s.post(f"{BASE}/quizzes/{quiz_id}/questions", json={
        "question_type": "coding_challenge",
        "text": "Implement fizzbuzz",
        "git_repo_url": "https://github.com/octocat/Hello-World",
        "test_command": "pytest",
        "time_budget_seconds": BUDGET_SECONDS,
    })
    if r.status_code not in (200, 201):
        print(f"FATAL: create question failed: {r.status_code} {r.text[:300]}")
        s.delete(f"{BASE}/quizzes/{quiz_id}")
        sys.exit(1)
    question_id = r.json()["id"]
    print(f"{INFO} Created question {question_id} (time_budget_seconds={BUDGET_SECONDS})")

    email = f"submit-ext-check-{int(time.time())}@example.com"
    r = s.post(f"{BASE}/quizzes/{quiz_id}/coding-challenge/invite", json={"candidate_emails": [email]})
    if r.status_code != 200:
        print(f"FATAL: invite failed: {r.status_code} {r.text[:300]}")
        s.delete(f"{BASE}/quizzes/{quiz_id}")
        sys.exit(1)
    invite_url = r.json()[0]["invite_url"]
    token = invite_url.rsplit("/", 1)[-1]
    payload = decode_jwt_payload(token)
    jti = payload["jti"]
    print(f"{INFO} Invited {email}, attempt_number={payload.get('attempt_number')}")

    anon = requests.Session()
    r = anon.post(f"{BASE}/coding-challenge/{token}/request-otp")
    if r.status_code != 200:
        print(f"FATAL: request-otp failed: {r.status_code} {r.text[:300]}")
        s.delete(f"{BASE}/quizzes/{quiz_id}")
        sys.exit(1)
    otp_key = f"coding_challenge_otp:{jti}:{email.lower()}"
    raw = r_client.get(otp_key)
    if not raw:
        print(f"FATAL: OTP not found in Redis at {otp_key}")
        s.delete(f"{BASE}/quizzes/{quiz_id}")
        sys.exit(1)
    otp = json.loads(raw)["otp"]

    print(f"{INFO} Firing /start...")
    r = anon.post(f"{BASE}/coding-challenge/{token}/start",
                   json={"ide_type": "code_server", "otp": otp}, timeout=30)
    if not check("/start returns 200", r.status_code == 200):
        print(f"  body: {r.text[:300]}")
        s.delete(f"{BASE}/quizzes/{quiz_id}")
        sys.exit(1)

    workspace_name = None
    workspace_url = None
    t0 = time.time()
    while time.time() - t0 < 180:
        r = anon.get(f"{BASE}/coding-challenge/{token}/status", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "provision_failed":
                check("provisioning succeeded", False)
                print(f"  provision_failed: {data}")
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
    print(f"{INFO} workspace_url: {workspace_url}")

    # ── T09: session.json check, directly on the real container ──
    stdout, stderr, rc = coder_ssh(workspace_name, "cat /home/coder/.swaya/session.json")
    check("session.json exists and is readable via coder ssh", rc == 0 and stdout.strip())
    if rc != 0:
        print(f"  stderr: {stderr[:300]}")

    session_data = {}
    if stdout.strip():
        try:
            session_data = json.loads(stdout)
            check("session.json is valid JSON", True)
        except Exception as e:
            check("session.json is valid JSON", False)
            print(f"  raw content: {stdout[:300]}  parse error: {e}")

    if session_data:
        check("apiBase matches test API base", session_data.get("apiBase") == BASE)
        ext_payload = decode_jwt_payload(session_data.get("inviteToken", ""))
        check("inviteToken decodes with matching quiz_id/question_id/candidate_email",
              ext_payload.get("quiz_id") == quiz_id
              and ext_payload.get("question_id") == question_id
              and ext_payload.get("candidate_email") == email.lower())
        check("timeBudgetSeconds matches configured budget",
              session_data.get("timeBudgetSeconds") == BUDGET_SECONDS)
        check("createdAt is present and parses", bool(session_data.get("createdAt")))
        print(f"{INFO} session.json: {json.dumps(session_data, indent=2)}")

    stdout, stderr, rc = coder_ssh(workspace_name, "stat -c '%a' /home/coder/.swaya/session.json")
    check("session.json is chmod 600", rc == 0 and stdout.strip() == "600")

    print()
    if issues:
        print(f"{FAIL} {len(issues)} issue(s): {issues}")
    else:
        print(f"{PASS} All Phase 1 (T09) checks passed.")

    if KEEP:
        print(f"\n{INFO} --keep passed: leaving quiz {quiz_id} and workspace {workspace_name} alive.")
        print(f"{INFO} Candidate invite token (for manual /submit testing later): {token}")
        print(f"{INFO} To clean up later: coder delete {workspace_name} -y  &&  "
              f"curl -X DELETE {BASE}/quizzes/{quiz_id} -H 'Authorization: Bearer <token>'")
    else:
        print(f"\n{INFO} Cleaning up...")
        try:
            subprocess.run(["coder", "delete", workspace_name, "-y"], capture_output=True, timeout=30)
        except Exception as e:
            print(f"  workspace delete raised {e}")
        r = s.delete(f"{BASE}/quizzes/{quiz_id}")
        print(f"{INFO} DELETE quiz {quiz_id} -> {r.status_code}")

    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()

"""
Coding-challenge /start concurrency smoke check.

/start used to block each candidate for up to ~150s+ doing the real Coder
provisioning inline (create_workspace + wait_for_app_ready + mint_session_url),
which is exactly what let nginx's proxy_read_timeout race a slow-but-successful
provision under concurrency and hand a candidate a false failure. /start now
acks fast and does the real work in a background job (provision_workspace_job),
so this script fires N (default 2 — deliberately well under
MAX_CONCURRENT_WORKSPACES so it doesn't compete with real candidate traffic on a
shared Coder sandbox) *real* concurrent /start calls via the actual invite -> OTP
-> start flow (OTP read directly out of Redis, since this only ever targets our
own test infra), then polls /status the same way the real frontend does — THAT
poll result is the actual acceptance test (a candidate must eventually reach a
real workspace_url or an honest provision_failed, never hang or get a false
failure while a workspace silently succeeds server-side). A separate thread
hammers an unrelated light endpoint throughout to prove the app stays
responsive. Cleans up every quiz + Coder workspace it creates, even on failure.

TEST ONLY by design — never point SWAYA_API_BASE at www.swaya.me for this one;
it provisions real Coder workspaces on the shared sandbox, unlike api_sweep.py.

Usage:
    TOKEN=$(cd backend && source .venv/bin/activate && \\
        python /home/vinay/Swaya.me/scripts/generate_selenium_token.py meetnishant@gmail.com)
    SWAYA_API_BASE=https://test.swaya.me/api/v1 SWAYA_TOKEN="$TOKEN" \\
        python scripts/coding_challenge_concurrency_check.py [N]
"""
import base64
import json
import os
import random
import string
import subprocess
import sys
import threading
import time

import redis
import requests

BASE = os.environ.get("SWAYA_API_BASE", "https://test.swaya.me/api/v1")
TOKEN = os.environ.get("SWAYA_TOKEN", "").strip()
N = int(sys.argv[1]) if len(sys.argv) > 1 else 2

if "www.swaya.me" in BASE:
    print("FATAL: refusing to run against www.swaya.me — this provisions real Coder")
    print("       workspaces on the shared sandbox. Run against test.swaya.me only.")
    sys.exit(1)
if not TOKEN:
    print("FATAL: SWAYA_TOKEN env var not set")
    sys.exit(1)

H = {"Authorization": f"Bearer {TOKEN}"}
r_client = redis.Redis(host="localhost", port=6379, db=0)


def rid(n=6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def decode_jwt_payload(token):
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def setup_candidate(s):
    """Create a quiz+question+invite, request OTP, read it from Redis. Always
    returns a dict — "ok": False on any failure, but with quiz_id populated
    as soon as it's known, not just on full success. A quiz created here and
    then orphaned by a LATER step failing (question/invite/OTP) used to be
    silently untracked and never cleaned up, since the old version returned
    a bare None on any failure, losing the quiz_id it had already created."""
    result = {"ok": False, "quiz_id": None, "question_id": None, "email": None,
              "token": None, "otp": None, "workspace_name": None}

    title = f"concurrency-check-{rid()}"
    r = s.post(f"{BASE}/quizzes/", json={"title": title, "quiz_type": "coding_challenge"})
    if r.status_code not in (200, 201):
        print(f"  setup FAILED (create quiz): {r.status_code} {r.text[:200]}")
        return result
    result["quiz_id"] = quiz_id = r.json()["id"]

    r = s.post(f"{BASE}/quizzes/{quiz_id}/questions", json={
        "question_type": "coding_challenge",
        "text": "Implement fizzbuzz",
        "git_repo_url": "https://github.com/octocat/Hello-World",
        "test_command": "pytest",
    })
    if r.status_code not in (200, 201):
        print(f"  setup FAILED (create question): {r.status_code} {r.text[:200]}")
        return result
    result["question_id"] = question_id = r.json()["id"]

    email = f"concurrency-check-{rid()}@example.com"
    r = s.post(f"{BASE}/quizzes/{quiz_id}/coding-challenge/invite", json={"candidate_emails": [email]})
    if r.status_code != 200:
        print(f"  setup FAILED (invite): {r.status_code} {r.text[:200]}")
        return result
    invite_url = r.json()[0]["invite_url"]
    token = invite_url.rsplit("/", 1)[-1]
    payload = decode_jwt_payload(token)
    jti = payload["jti"]

    anon = requests.Session()
    r = anon.post(f"{BASE}/coding-challenge/{token}/request-otp")
    if r.status_code != 200:
        print(f"  setup FAILED (request-otp): {r.status_code} {r.text[:200]}")
        return result

    otp_key = f"coding_challenge_otp:{jti}:{email.lower()}"
    raw = r_client.get(otp_key)
    if not raw:
        print(f"  setup FAILED: OTP not found in Redis at {otp_key}")
        return result
    otp = json.loads(raw)["otp"]

    result.update({"ok": True, "email": email, "token": token, "otp": otp})
    return result


def cleanup(s, candidates):
    for c in candidates:
        if not c or not c.get("quiz_id"):
            continue
        try:
            r = s.delete(f"{BASE}/quizzes/{c['quiz_id']}")
            print(f"  cleanup: DELETE quiz {c['quiz_id']} -> {r.status_code}")
        except Exception as e:
            print(f"  cleanup: DELETE quiz {c['quiz_id']} raised {e}")
        # The quiz delete above does not necessarily tear down the Coder
        # workspace itself — best-effort direct cleanup too.
        try:
            subprocess.run(["coder", "delete", c["workspace_name"], "-y"],
                            capture_output=True, timeout=30) if c.get("workspace_name") else None
        except Exception:
            pass


def poll_light_endpoint(stop_event, results):
    """Runs in its own thread for the duration of the concurrent /start calls —
    proves the app keeps serving unrelated requests promptly throughout."""
    anon = requests.Session()
    while not stop_event.is_set():
        t0 = time.time()
        try:
            r = anon.get(f"{BASE}/auth/tier-plans", timeout=10)
            elapsed = time.time() - t0
            results.append((elapsed, r.status_code))
        except Exception as e:
            results.append((time.time() - t0, f"ERROR: {e}"))
        time.sleep(2)


def do_start(c, results, idx):
    """Fires /start and records its (now fast, sub-second) ack. /start no longer
    does the actual Coder provisioning inline — see wait_for_ready below for the
    real pass/fail signal."""
    anon = requests.Session()
    t0 = time.time()
    try:
        r = anon.post(f"{BASE}/coding-challenge/{c['token']}/start",
                       json={"ide_type": "code_server", "otp": c["otp"]}, timeout=30)
        elapsed = time.time() - t0
        results[idx] = (elapsed, r.status_code, r.text[:300])
        if r.status_code == 200:
            c["workspace_name"] = f"cc-{c['quiz_id']}-{c['question_id']}-" + \
                __import__("hashlib").sha256(f"{c['email'].lower()}:1".encode()).hexdigest()[:8]
    except Exception as e:
        results[idx] = (time.time() - t0, "EXC", str(e))


READY_TIMEOUT_S = 180  # generous margin over the old 150s nginx timeout this replaces


def wait_for_ready(c, ready_results, idx):
    """/start now just acks fast and kicks off provisioning in the background —
    this polls /status the same way the real frontend does, and IS the actual
    acceptance test for the fix: a candidate must eventually reach a real
    workspace_url (or an honest provision_failed), never hang forever or get a
    false failure while a workspace silently succeeds server-side."""
    anon = requests.Session()
    t0 = time.time()
    while time.time() - t0 < READY_TIMEOUT_S:
        try:
            r = anon.get(f"{BASE}/coding-challenge/{c['token']}/status", timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "provision_failed":
                    ready_results[idx] = ("provision_failed", time.time() - t0, data)
                    return
                if data.get("workspace_url"):
                    ready_results[idx] = ("ready", time.time() - t0, data)
                    return
        except Exception:
            pass  # transient poll failure — keep trying until the timeout, matching the frontend
        time.sleep(2)
    ready_results[idx] = ("timeout", time.time() - t0, None)


def main():
    s = requests.Session()
    s.headers.update(H)

    print(f"Target: {BASE}  |  N={N} concurrent /start calls\n")

    print(f"Setting up {N} candidates (quiz + question + invite + OTP)...")
    candidates = [setup_candidate(s) for _ in range(N)]
    if any(not c["ok"] for c in candidates):
        print("\nFATAL: setup failed for at least one candidate — aborting before firing /start.")
        print("Cleaning up whatever WAS created (quiz/question/invite may exist even for a")
        print("candidate whose setup ultimately failed at a later step)...")
        cleanup(s, candidates)
        sys.exit(1)
    print("Setup OK for all candidates.\n")

    all_started_ok = False
    all_ready_ok = False
    slow = []
    poll_results = []
    try:
        stop_event = threading.Event()
        poll_thread = threading.Thread(target=poll_light_endpoint, args=(stop_event, poll_results), daemon=True)
        poll_thread.start()

        start_results = [None] * N
        threads = []
        t_begin = time.time()
        print(f"Firing {N} concurrent /start calls...")
        for i, c in enumerate(candidates):
            th = threading.Thread(target=do_start, args=(c, start_results, i))
            threads.append(th)
            th.start()
        for th in threads:
            th.join()
        t_ack = time.time() - t_begin

        print(f"\n/start acks finished in {t_ack:.1f}s total (concurrent, not summed) — "
              f"expected to be fast now, real provisioning happens in the background:")
        all_started_ok = True
        for i, res in enumerate(start_results):
            elapsed, status, body = res
            ok = status == 200
            all_started_ok = all_started_ok and ok
            print(f"  [{'PASS' if ok else 'FAIL'}] candidate {i}: {elapsed:.1f}s status={status} {body if not ok else ''}")

        print(f"\nPolling /status for real readiness (up to {READY_TIMEOUT_S}s each) — "
              f"this is the actual acceptance test, not the fast ack above...")
        ready_results = [None] * N
        ready_threads = []
        for i, c in enumerate(candidates):
            if start_results[i][1] != 200:
                ready_results[i] = ("skipped", 0, None)
                continue
            th = threading.Thread(target=wait_for_ready, args=(c, ready_results, i))
            ready_threads.append(th)
            th.start()
        for th in ready_threads:
            th.join()
        t_total = time.time() - t_begin

        stop_event.set()
        poll_thread.join(timeout=5)

        all_ready_ok = True
        for i, res in enumerate(ready_results):
            outcome, elapsed, data = res
            ok = outcome == "ready"
            all_ready_ok = all_ready_ok and ok
            detail = f"status={data.get('status')}" if data else ""
            print(f"  [{'PASS' if ok else 'FAIL'}] candidate {i}: {outcome} after {elapsed:.1f}s {detail}")

        print(f"\nLight-endpoint responsiveness during the full {t_total:.1f}s window "
              f"({len(poll_results)} polls of GET /auth/tier-plans):")
        slow = [p for p in poll_results if isinstance(p[1], str) or p[0] > 3.0]
        for elapsed, status in poll_results:
            flag = "SLOW" if (isinstance(status, str) or elapsed > 3.0) else "ok"
            print(f"  [{flag}] {elapsed:.2f}s status={status}")
    except Exception as e:
        print(f"\nFATAL: uncaught exception during firing/polling: {type(e).__name__}: {e}")
    finally:
        # Runs even on an uncaught exception above — every workspace this
        # script provisions must be torn down regardless of how the run ends.
        print("\nCleaning up...")
        cleanup(s, candidates)

    print("\n==== SUMMARY ====")
    print(f"All {N} /start calls acked: {all_started_ok}")
    print(f"All {N} workspaces actually became ready: {all_ready_ok}")
    print(f"Light-endpoint polls that were slow (>3s) or errored: {len(slow)} / {len(poll_results)}")

    if not all_started_ok or not all_ready_ok or slow:
        sys.exit(1)


if __name__ == "__main__":
    main()

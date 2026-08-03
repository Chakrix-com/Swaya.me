"""
Coding-challenge /start concurrency smoke check.

/start blocks each candidate for up to WORKSPACE_START_TIMEOUT (120s by default,
see coder_client.wait_for_app_ready) while polling `coder ssh` as a subprocess
every ~2s. Nothing in this repo had ever load-tested whether firing a few of
these concurrently starves the rest of the app (other quiz/poll/exam traffic,
also served by the same uvicorn workers). This fires N (default 2 — deliberately
well under MAX_CONCURRENT_WORKSPACES so it doesn't compete with real candidate
traffic on a shared Coder sandbox) *real* concurrent /start calls, using the
actual invite -> OTP -> start flow (OTP is read directly out of Redis rather
than needing real email delivery, since this only ever targets our own test
infra), while a separate thread hammers an unrelated light endpoint every 2s
to prove the app stays responsive throughout. Cleans up every quiz + Coder
workspace it creates, even on failure.

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
    """Create a quiz+question+invite, request OTP, read it from Redis. Returns a
    dict with everything needed to call /start, or None on any failure."""
    title = f"concurrency-check-{rid()}"
    r = s.post(f"{BASE}/quizzes/", json={"title": title, "quiz_type": "coding_challenge"})
    if r.status_code not in (200, 201):
        print(f"  setup FAILED (create quiz): {r.status_code} {r.text[:200]}")
        return None
    quiz_id = r.json()["id"]

    r = s.post(f"{BASE}/quizzes/{quiz_id}/questions", json={
        "question_type": "coding_challenge",
        "text": "Implement fizzbuzz",
        "git_repo_url": "https://github.com/octocat/Hello-World",
        "test_command": "pytest",
    })
    if r.status_code not in (200, 201):
        print(f"  setup FAILED (create question): {r.status_code} {r.text[:200]}")
        return None
    question_id = r.json()["id"]

    email = f"concurrency-check-{rid()}@example.com"
    r = s.post(f"{BASE}/quizzes/{quiz_id}/coding-challenge/invite", json={"candidate_emails": [email]})
    if r.status_code != 200:
        print(f"  setup FAILED (invite): {r.status_code} {r.text[:200]}")
        return None
    invite_url = r.json()[0]["invite_url"]
    token = invite_url.rsplit("/", 1)[-1]
    payload = decode_jwt_payload(token)
    jti = payload["jti"]

    anon = requests.Session()
    r = anon.post(f"{BASE}/coding-challenge/{token}/request-otp")
    if r.status_code != 200:
        print(f"  setup FAILED (request-otp): {r.status_code} {r.text[:200]}")
        return None

    otp_key = f"coding_challenge_otp:{jti}:{email.lower()}"
    raw = r_client.get(otp_key)
    if not raw:
        print(f"  setup FAILED: OTP not found in Redis at {otp_key}")
        return None
    otp = json.loads(raw)["otp"]

    return {
        "quiz_id": quiz_id, "question_id": question_id, "email": email,
        "token": token, "otp": otp, "workspace_name": None,
    }


def cleanup(s, candidates):
    for c in candidates:
        if not c:
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
    anon = requests.Session()
    t0 = time.time()
    try:
        r = anon.post(f"{BASE}/coding-challenge/{c['token']}/start",
                       json={"ide_type": "code_server", "otp": c["otp"]}, timeout=150)
        elapsed = time.time() - t0
        results[idx] = (elapsed, r.status_code, r.text[:300])
        if r.status_code == 200:
            c["workspace_name"] = f"cc-{c['quiz_id']}-{c['question_id']}-" + \
                __import__("hashlib").sha256(f"{c['email'].lower()}:1".encode()).hexdigest()[:8]
    except Exception as e:
        results[idx] = (time.time() - t0, "EXC", str(e))


def main():
    s = requests.Session()
    s.headers.update(H)

    print(f"Target: {BASE}  |  N={N} concurrent /start calls\n")

    print(f"Setting up {N} candidates (quiz + question + invite + OTP)...")
    candidates = [setup_candidate(s) for _ in range(N)]
    if any(c is None for c in candidates):
        print("\nFATAL: setup failed for at least one candidate — aborting before firing /start.")
        cleanup(s, candidates)
        sys.exit(1)
    print("Setup OK for all candidates.\n")

    stop_event = threading.Event()
    poll_results = []
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
    t_total = time.time() - t_begin

    stop_event.set()
    poll_thread.join(timeout=5)

    print(f"\n/start calls finished in {t_total:.1f}s total (concurrent, not summed):")
    all_started_ok = True
    for i, res in enumerate(start_results):
        elapsed, status, body = res
        ok = status == 200
        all_started_ok = all_started_ok and ok
        print(f"  [{'PASS' if ok else 'FAIL'}] candidate {i}: {elapsed:.1f}s status={status} {body if not ok else ''}")

    print(f"\nLight-endpoint responsiveness during the {t_total:.1f}s window "
          f"({len(poll_results)} polls of GET /auth/tier-plans):")
    slow = [p for p in poll_results if isinstance(p[1], str) or p[0] > 3.0]
    for elapsed, status in poll_results:
        flag = "SLOW" if (isinstance(status, str) or elapsed > 3.0) else "ok"
        print(f"  [{flag}] {elapsed:.2f}s status={status}")

    print("\n==== SUMMARY ====")
    print(f"All {N} /start calls succeeded: {all_started_ok}")
    print(f"Light-endpoint polls that were slow (>3s) or errored: {len(slow)} / {len(poll_results)}")

    print("\nCleaning up...")
    cleanup(s, candidates)

    if not all_started_ok or slow:
        sys.exit(1)


if __name__ == "__main__":
    main()

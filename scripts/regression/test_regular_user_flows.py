#!/usr/bin/env python3
"""
Regular User Full Lifecycle Test
Tests create quiz → add MCQ + word cloud → publish → session → audience → answer → leaderboard → end → results
Runs as REGULAR_USER_EMAIL (role=user, tier=FREE) to catch bugs that only manifest for non-admin users.
"""
import os
import sys
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = os.getenv("BASE_URL", "https://test.swaya.me/api/v1").rstrip("/")
EMAIL = os.getenv("REGULAR_USER_EMAIL", "regression-free@swaya.me")
PASSWORD = os.getenv("REGULAR_USER_PASSWORD", "RegTest2026!")


def fail(msg: str):
    print(f"FAIL: {msg}")
    sys.exit(1)


def check(cond: bool, msg: str):
    if not cond:
        fail(msg)


def _end_open_sessions(s: requests.Session):
    """End all CREATED/ACTIVE sessions to clear the concurrent limit for FREE tier."""
    r = s.get(f"{BASE_URL}/quizzes/", timeout=20)
    if r.status_code != 200:
        return
    for quiz in r.json():
        qid = quiz.get("id")
        sessions_r = s.get(f"{BASE_URL}/quizzes/{qid}/sessions", timeout=20)
        if sessions_r.status_code != 200:
            continue
        for sess in sessions_r.json().get("sessions", []):
            if sess.get("status") in ("created", "active"):
                s.post(f"{BASE_URL}/quizzes/sessions/{sess['id']}/end", timeout=20)


def main():
    s = requests.Session()
    s.verify = False

    # 1. Login as regular user
    r = s.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    check(r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}")
    token = r.json().get("access_token")
    check(bool(token) and token != "pending_verification", f"bad token: {token}")
    s.headers["Authorization"] = f"Bearer {token}"
    print("OK: login")

    # End any stale open sessions to avoid FREE tier concurrent limit
    _end_open_sessions(s)
    print("OK: cleared open sessions")

    # 2. /auth/me
    r = s.get(f"{BASE_URL}/auth/me", timeout=20)
    check(r.status_code == 200, f"/auth/me failed: {r.status_code}")
    me = r.json()
    check(me.get("role") in ("user", "admin", "super_admin"), f"unexpected role: {me.get('role')}")
    print(f"OK: /auth/me  role={me['role']}")

    # 3. Create a quiz
    r = s.post(f"{BASE_URL}/quizzes/", json={"title": "RegTest Lifecycle Quiz", "description": "auto"}, timeout=20)
    check(r.status_code in (200, 201), f"create quiz failed: {r.status_code} {r.text[:200]}")
    quiz_id = r.json()["id"]
    print(f"OK: create quiz  id={quiz_id}")

    # 4. Add MCQ question
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "What is 2+2?",
        "question_type": "mcq",
        "options": ["3", "4", "5", "6"],
        "correct_answer_index": 1,
        "max_time_seconds": 20,
        "points": 100,
    }, timeout=20)
    check(r.status_code in (200, 201), f"add MCQ failed: {r.status_code} {r.text[:300]}")
    mcq_id = r.json()["id"]
    print(f"OK: add MCQ question  id={mcq_id}")

    # 5. Add word cloud question
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "What comes to mind when you think of testing?",
        "question_type": "word_cloud",
        "max_time_seconds": 30,
        "points": 1,
    }, timeout=20)
    check(r.status_code in (200, 201), f"add word cloud failed: {r.status_code} {r.text[:300]}")
    wc_id = r.json()["id"]
    print(f"OK: add word cloud question  id={wc_id}")

    # 6. Get quiz (verify questions saved)
    r = s.get(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)
    check(r.status_code == 200, f"get quiz failed: {r.status_code}")
    qs = r.json().get("questions", [])
    check(len(qs) >= 2, f"expected >=2 questions, got {len(qs)}")
    print(f"OK: get quiz  questions={len(qs)}")

    # 7. Publish quiz (DRAFT → READY)
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/publish", timeout=20)
    check(r.status_code in (200, 201), f"publish failed: {r.status_code} {r.text[:200]}")
    print("OK: publish")

    # 8. Start session
    r = s.post(f"{BASE_URL}/quizzes/sessions/start", params={"quiz_id": quiz_id}, timeout=20)
    check(r.status_code in (200, 201), f"start session failed: {r.status_code} {r.text[:200]}")
    session_id = r.json()["id"]
    join_code = r.json()["join_code"]
    print(f"OK: start session  id={session_id}  join_code={join_code}")

    # 9. Audience join (anonymous, no auth)
    anon = requests.Session()
    anon.verify = False
    r = anon.post(f"{BASE_URL}/quizzes/sessions/join",
                  json={"join_code": join_code, "display_name": "RegTestUser"}, timeout=20)
    check(r.status_code == 200, f"audience join failed: {r.status_code} {r.text[:200]}")
    p_token = r.json()["session_token"]
    print(f"OK: audience join  token={p_token[:12]}…")

    # 10. Advance to first question
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/advance", timeout=20)
    check(r.status_code in (200, 201), f"advance failed: {r.status_code}")
    print("OK: advance to Q1")

    # 11. Submit MCQ answer
    r = anon.post(f"{BASE_URL}/quizzes/sessions/submit-answer",
                  params={"session_token": p_token},
                  json={"question_id": mcq_id, "selected_option_index": 1},
                  timeout=20)
    check(r.status_code in (200, 201), f"submit MCQ answer failed: {r.status_code} {r.text[:200]}")
    print("OK: submit MCQ answer")

    # 12. Leaderboard
    r = s.get(f"{BASE_URL}/quizzes/sessions/{session_id}/leaderboard", timeout=20)
    check(r.status_code == 200, f"leaderboard failed: {r.status_code}")
    print("OK: leaderboard")

    # 13. End session
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/end", timeout=20)
    check(r.status_code in (200, 201), f"end session failed: {r.status_code}")
    print("OK: end session")

    # 14. Results
    r = s.get(f"{BASE_URL}/quizzes/sessions/{session_id}/results", timeout=20)
    check(r.status_code == 200, f"results failed: {r.status_code}")
    print("OK: results")

    # 15. Session feedback (from participant)
    r = anon.post(f"{BASE_URL}/quizzes/sessions/feedback",
                  params={"session_token": p_token},
                  json={"feedback_text": "great test", "rating": 5, "session_id": session_id},
                  timeout=20)
    check(r.status_code in (200, 201), f"feedback failed: {r.status_code} {r.text[:200]}")
    print("OK: session feedback")

    # 16. Cleanup: unpublish (→ DRAFT) then delete
    # Note: quizzes with session history may not be deletable (DB constraint) — best-effort
    s.post(f"{BASE_URL}/quizzes/{quiz_id}/unpublish", timeout=20)
    s.delete(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)
    print("OK: cleanup (best-effort)")

    print("\nOK: regular_user_flows — all steps passed")


if __name__ == "__main__":
    main()

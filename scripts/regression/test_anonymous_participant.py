#!/usr/bin/env python3
"""
Anonymous Participant Regression Test
Tests that a participant can join a session without providing a display_name,
and that the system handles the missing name gracefully:
  - Join with no display_name: should succeed, backend falls back to 'Guest'
  - Join with empty string display_name: should succeed
  - The anonymous participant appears in leaderboard with fallback name (not null/empty)
  - The participant can submit answers successfully
Runs as REGULAR_USER_EMAIL (role=user, tier=FREE).
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

    # Login
    r = s.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    check(r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}")
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    print("OK: login")

    _end_open_sessions(s)
    print("OK: cleared open sessions")

    # Create and publish a quiz
    r = s.post(f"{BASE_URL}/quizzes/", json={"title": "Anonymous Participant Regression"}, timeout=20)
    check(r.status_code in (200, 201), f"create quiz failed: {r.status_code}")
    quiz_id = r.json()["id"]
    print(f"OK: create quiz  id={quiz_id}")

    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "Quick check — which option is correct?",
        "question_type": "mcq",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer_index": 0,
        "points": 10,
    }, timeout=20)
    check(r.status_code in (200, 201), f"add question failed: {r.status_code}")
    question_id = r.json()["id"]
    print(f"OK: add question  id={question_id}")

    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/publish", timeout=20)
    check(r.status_code in (200, 201), f"publish failed: {r.status_code}")
    print("OK: published")

    r = s.post(f"{BASE_URL}/quizzes/sessions/start", params={"quiz_id": quiz_id}, timeout=20)
    check(r.status_code in (200, 201), f"start session failed: {r.status_code}")
    session_id = r.json()["id"]
    join_code = r.json()["join_code"]
    print(f"OK: session started  id={session_id}  join_code={join_code}")

    # ── Test 1: Join with no display_name field at all ────────────────────────
    anon1 = requests.Session()
    anon1.verify = False
    r = anon1.post(f"{BASE_URL}/quizzes/sessions/join",
                   json={"join_code": join_code}, timeout=20)
    check(r.status_code == 200, f"join without display_name failed: {r.status_code} {r.text[:200]}")
    p_token1 = r.json()["session_token"]
    check(bool(p_token1), "no session_token for anonymous participant")
    print(f"OK: joined without display_name  token={p_token1[:12]}…")

    # ── Test 2: Join with empty string display_name ───────────────────────────
    anon2 = requests.Session()
    anon2.verify = False
    r = anon2.post(f"{BASE_URL}/quizzes/sessions/join",
                   json={"join_code": join_code, "display_name": ""}, timeout=20)
    check(r.status_code == 200, f"join with empty display_name failed: {r.status_code} {r.text[:200]}")
    p_token2 = r.json()["session_token"]
    check(bool(p_token2), "no session_token for empty-name participant")
    print(f"OK: joined with empty display_name  token={p_token2[:12]}…")

    # ── Test 3: Named participant for comparison ───────────────────────────────
    anon3 = requests.Session()
    anon3.verify = False
    r = anon3.post(f"{BASE_URL}/quizzes/sessions/join",
                   json={"join_code": join_code, "display_name": "NamedParticipant"}, timeout=20)
    check(r.status_code == 200, f"join with name failed: {r.status_code}")
    p_token3 = r.json()["session_token"]
    print(f"OK: named participant joined  token={p_token3[:12]}…")

    # Advance to question and all three participants answer
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/advance", timeout=20)
    check(r.status_code in (200, 201), f"advance failed: {r.status_code}")
    print("OK: advanced to question")

    for token, label in [(p_token1, "anon-no-name"), (p_token2, "anon-empty"), (p_token3, "named")]:
        r = requests.Session()
        r.verify = False
        resp = r.post(f"{BASE_URL}/quizzes/sessions/submit-answer",
                      params={"session_token": token},
                      json={"question_id": question_id, "selected_option_index": 0},
                      timeout=20)
        check(resp.status_code in (200, 201), f"{label} answer failed: {resp.status_code} {resp.text[:200]}")
    print("OK: all 3 participants answered")

    # Leaderboard: anonymous participants should have a non-empty fallback name
    r = s.get(f"{BASE_URL}/quizzes/sessions/{session_id}/leaderboard", timeout=20)
    check(r.status_code == 200, f"leaderboard failed: {r.status_code}")
    entries = r.json().get("entries", [])
    check(len(entries) >= 3, f"expected >=3 leaderboard entries, got {len(entries)}")

    for entry in entries:
        name = entry.get("display_name", "")
        check(bool(name), f"leaderboard entry has empty display_name: {entry}")
    print(f"OK: all {len(entries)} leaderboard entries have non-empty display_name")

    # Verify named participant shows their actual name
    named_entry = next((e for e in entries if e.get("display_name") == "NamedParticipant"), None)
    check(named_entry is not None, "named participant 'NamedParticipant' not found in leaderboard")
    print("OK: named participant correctly appears in leaderboard")

    # Audience-results: anonymous participant can poll their own state
    anon_s = requests.Session()
    anon_s.verify = False
    r = anon_s.get(f"{BASE_URL}/quizzes/sessions/{session_id}/audience-results",
                   params={"session_token": p_token1}, timeout=20)
    check(r.status_code == 200, f"audience-results for anon failed: {r.status_code} {r.text[:200]}")
    print("OK: anonymous participant can fetch audience-results")

    # End session
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/end", timeout=20)
    check(r.status_code in (200, 201), f"end session failed: {r.status_code}")
    print("OK: end session")

    # Cleanup
    s.post(f"{BASE_URL}/quizzes/{quiz_id}/unpublish", timeout=20)
    s.delete(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)
    print("OK: cleanup (best-effort)")

    print("\nOK: anonymous_participant — all steps passed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Offline Poll Lifecycle Test
Tests: publish-offline, get info, join, answer, complete, results
Runs as REGULAR_USER_EMAIL (role=user, tier=FREE).
"""
import os
import sys
import requests
import urllib3
from datetime import datetime, timezone, timedelta

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


def main():
    s = requests.Session()
    s.verify = False

    r = s.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    check(r.status_code == 200, f"login failed: {r.status_code}")
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    print("OK: login")

    # Create quiz with one MCQ question (must use quiz_type=offline_poll with date window)
    now = datetime.now(timezone.utc)
    r = s.post(f"{BASE_URL}/quizzes/", json={
        "title": "OfflinePoll Lifecycle Test",
        "quiz_type": "offline_poll",
        "offline_start_at": now.isoformat(),
        "offline_end_at": (now + timedelta(days=7)).isoformat(),
    }, timeout=20)
    check(r.status_code in (200, 201), f"create quiz failed: {r.status_code} {r.text[:200]}")
    quiz_id = r.json()["id"]
    print(f"OK: create quiz  id={quiz_id}")

    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "Best testing framework?",
        "question_type": "mcq",
        "options": ["pytest", "unittest", "nose", "doctest"],
        "correct_answer_index": 0,
        "max_time_seconds": 60,
        "points": 100,
    }, timeout=20)
    check(r.status_code in (200, 201), f"add question failed: {r.status_code} {r.text[:200]}")
    question_id = r.json()["id"]
    print(f"OK: add question  id={question_id}")

    # Publish as offline poll
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/publish-offline", timeout=20)
    check(r.status_code in (200, 201), f"publish-offline failed: {r.status_code} {r.text[:300]}")
    slug = r.json().get("poll_slug")
    check(bool(slug), "no slug returned from publish-offline")
    print(f"OK: publish-offline  slug={slug}")

    # Get poll info (public — no auth)
    anon = requests.Session()
    anon.verify = False
    r = anon.get(f"{BASE_URL}/offline-poll/{slug}", timeout=20)
    check(r.status_code == 200, f"get poll info failed: {r.status_code} {r.text[:200]}")
    print(f"OK: get poll info  status={r.json().get('status')}")

    # Join poll
    r = anon.post(f"{BASE_URL}/offline-poll/{slug}/join", json={"display_name": "PollTester"}, timeout=20)
    check(r.status_code == 200, f"join poll failed: {r.status_code} {r.text[:200]}")
    p_token = r.json().get("session_token")
    check(bool(p_token), "no session_token from join")
    print(f"OK: join poll  token={p_token[:12]}…")

    # Get questions from join response or poll info
    questions = r.json().get("questions", [])
    if not questions:
        info_r = anon.get(f"{BASE_URL}/offline-poll/{slug}", timeout=20)
        questions = info_r.json().get("questions", [])

    check(len(questions) > 0, "no questions returned for offline poll")
    q_id = questions[0]["id"]

    # Save answer
    r = anon.post(f"{BASE_URL}/offline-poll/{slug}/answer", json={
        "session_token": p_token,
        "question_id": q_id,
        "selected_option_index": 0,
    }, timeout=20)
    check(r.status_code in (200, 201), f"save answer failed: {r.status_code} {r.text[:200]}")
    print("OK: save answer")

    # Complete poll
    r = anon.post(f"{BASE_URL}/offline-poll/{slug}/complete", json={"session_token": p_token}, timeout=20)
    check(r.status_code in (200, 201), f"complete poll failed: {r.status_code} {r.text[:200]}")
    print("OK: complete poll")

    # Get results (authenticated host)
    r = s.get(f"{BASE_URL}/offline-poll/{slug}/results", timeout=20)
    check(r.status_code == 200, f"get results failed: {r.status_code} {r.text[:200]}")
    print(f"OK: get results  participants={r.json().get('total_participants', '?')}")

    # Cleanup (best-effort — offline poll quizzes may not be deletable after publish)
    s.delete(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)

    print("\nOK: offline_poll_lifecycle — all steps passed")


if __name__ == "__main__":
    main()

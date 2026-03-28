#!/usr/bin/env python3
"""
Exam Lifecycle Test
Tests: create quiz, add MCQ, publish-exam, get-info, start, answer, submit, result, host-results, unpublish-exam
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

    # Create quiz (must use quiz_type=exam with date window)
    now = datetime.now(timezone.utc)
    r = s.post(f"{BASE_URL}/quizzes/", json={
        "title": "Exam Lifecycle Test Quiz",
        "quiz_type": "exam",
        "exam_start_at": now.isoformat(),
        "exam_end_at": (now + timedelta(days=7)).isoformat(),
    }, timeout=20)
    check(r.status_code in (200, 201), f"create quiz failed: {r.status_code} {r.text[:200]}")
    quiz_id = r.json()["id"]
    print(f"OK: create quiz  id={quiz_id}")

    # Add MCQ question
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "Capital of France?",
        "question_type": "mcq",
        "options": ["Berlin", "Paris", "Madrid", "Rome"],
        "correct_answer_index": 1,
        "max_time_seconds": 60,
        "points": 10,
    }, timeout=20)
    check(r.status_code in (200, 201), f"add question failed: {r.status_code} {r.text[:200]}")
    question_id = r.json()["id"]
    print(f"OK: add question  id={question_id}")

    # Publish as exam
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/publish-exam", timeout=20)
    check(r.status_code in (200, 201), f"publish-exam failed: {r.status_code} {r.text[:300]}")
    slug = r.json().get("exam_slug")
    check(bool(slug), "no slug returned from publish-exam")
    print(f"OK: publish-exam  slug={slug}")

    # Get exam info (public)
    anon = requests.Session()
    anon.verify = False
    r = anon.get(f"{BASE_URL}/e/{slug}", timeout=20)
    check(r.status_code == 200, f"get exam info failed: {r.status_code} {r.text[:200]}")
    print(f"OK: get exam info  status={r.json().get('status')}")

    # Start exam (public)
    r = anon.post(f"{BASE_URL}/e/{slug}/start", json={"display_name": "ExamTester"}, timeout=20)
    check(r.status_code in (200, 201), f"start exam failed: {r.status_code} {r.text[:200]}")
    p_token = r.json().get("session_token")
    check(bool(p_token), "no session_token from exam start")
    questions = r.json().get("questions", [])
    check(len(questions) > 0, "no questions returned from exam start")
    q_id = questions[0]["id"]
    print(f"OK: start exam  token={p_token[:12]}…  questions={len(questions)}")

    # Save answer (autosave)
    r = anon.post(f"{BASE_URL}/e/{slug}/answer", json={
        "session_token": p_token,
        "question_id": q_id,
        "selected_option_index": 1,
    }, timeout=20)
    check(r.status_code in (200, 201), f"save answer failed: {r.status_code} {r.text[:200]}")
    print("OK: save exam answer")

    # Submit exam
    r = anon.post(f"{BASE_URL}/e/{slug}/submit", json={"session_token": p_token}, timeout=20)
    check(r.status_code in (200, 201), f"submit exam failed: {r.status_code} {r.text[:200]}")
    score = r.json().get("score")
    print(f"OK: submit exam  score={score}")

    # Get my result
    r = anon.post(f"{BASE_URL}/e/{slug}/result", json={"session_token": p_token}, timeout=20)
    check(r.status_code in (200, 201), f"get my result failed: {r.status_code} {r.text[:200]}")
    print(f"OK: get my result  score={r.json().get('score')}")

    # Host results (authenticated)
    r = s.get(f"{BASE_URL}/quiz/{quiz_id}/exam-results", timeout=20)
    check(r.status_code == 200, f"host exam-results failed: {r.status_code} {r.text[:200]}")
    print(f"OK: host exam-results  participants={len(r.json().get('leaderboard', []))}")

    # Unpublish exam (reverts to DRAFT)
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/unpublish-exam", timeout=20)
    check(r.status_code in (200, 201), f"unpublish-exam failed: {r.status_code} {r.text[:200]}")
    print("OK: unpublish-exam")

    # Cleanup
    s.delete(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)

    print("\nOK: exam_lifecycle — all steps passed")


if __name__ == "__main__":
    main()

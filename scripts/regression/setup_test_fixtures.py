#!/usr/bin/env python3
"""
Ensures test fixtures exist for the regular user persona.
- READY quiz with a word_cloud question (required by test_word_cloud_e2e.py)
- READY quiz with any questions (required by test_rejoin_simple.py)

Safe to run multiple times (idempotent).
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


def main():
    s = requests.Session()
    s.verify = False

    r = s.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    if r.status_code != 200:
        fail(f"login failed: {r.status_code} {r.text[:200]}")
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    print(f"OK: login as {EMAIL}")

    # List existing quizzes
    r = s.get(f"{BASE_URL}/quizzes/", timeout=20)
    if r.status_code != 200:
        fail(f"list quizzes failed: {r.status_code}")
    quizzes = r.json()

    # Check if we already have a READY quiz with word_cloud
    has_wc_ready = False
    has_any_ready = False
    for quiz in quizzes:
        if str(quiz.get("status", "")).lower() != "ready":
            continue
        has_any_ready = True
        # Get quiz detail
        qr = s.get(f"{BASE_URL}/quizzes/{quiz['id']}", timeout=20)
        if qr.status_code != 200:
            continue
        for q in qr.json().get("questions", []):
            if q.get("question_type") == "word_cloud":
                has_wc_ready = True
                break
        if has_wc_ready:
            break

    if has_wc_ready:
        print("OK: word_cloud READY quiz already exists — no setup needed")
        return

    print("INFO: creating READY quiz with word_cloud question for regular user...")

    # End any open sessions to stay under FREE tier limit
    for quiz in quizzes:
        sess_r = s.get(f"{BASE_URL}/quizzes/{quiz['id']}/sessions", timeout=20)
        if sess_r.status_code != 200:
            continue
        for sess in sess_r.json().get("sessions", []):
            if sess.get("status") in ("created", "active"):
                s.post(f"{BASE_URL}/quizzes/sessions/{sess['id']}/end", timeout=20)

    # Create quiz
    r = s.post(f"{BASE_URL}/quizzes/", json={"title": "Regression Fixture Quiz (word cloud)"}, timeout=20)
    if r.status_code not in (200, 201):
        fail(f"create quiz: {r.status_code} {r.text[:200]}")
    quiz_id = r.json()["id"]

    # Add MCQ question
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "What is your favorite color?",
        "question_type": "mcq",
        "options": ["Red", "Blue", "Green", "Yellow"],
        "correct_answer_index": 0,
        "max_time_seconds": 30,
        "points": 10,
    }, timeout=20)
    if r.status_code not in (200, 201):
        fail(f"add MCQ: {r.status_code} {r.text[:200]}")

    # Add word_cloud question
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "What word describes your experience?",
        "question_type": "word_cloud",
        "max_time_seconds": 30,
        "points": 1,
    }, timeout=20)
    if r.status_code not in (200, 201):
        fail(f"add word_cloud: {r.status_code} {r.text[:200]}")

    # Publish
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/publish", timeout=20)
    if r.status_code not in (200, 201):
        fail(f"publish: {r.status_code} {r.text[:200]}")

    print(f"OK: created and published word_cloud fixture quiz  id={quiz_id}")
    print("OK: setup_test_fixtures — done")


if __name__ == "__main__":
    main()

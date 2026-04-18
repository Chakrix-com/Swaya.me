#!/usr/bin/env python3
"""
Live Poll Lifecycle Test (quiz_type=poll)
Tests the live poll mode explicitly — previously only quiz/exam/offline_poll were covered.
Poll mode: no scoring, no leaderboard entries, participants can answer MCQ + word_cloud + scale.
Tests:
  - Create quiz with quiz_type=poll
  - Add MCQ, word_cloud, and scale questions
  - Publish, start session, join
  - Submit all question types
  - Verify leaderboard returns empty entries (polls have no scoring)
  - Verify results structure is correct
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

    # Create live poll quiz
    r = s.post(f"{BASE_URL}/quizzes/", json={
        "title": "Live Poll Lifecycle Regression",
        "quiz_type": "poll",
    }, timeout=20)
    check(r.status_code in (200, 201), f"create poll quiz failed: {r.status_code} {r.text[:200]}")
    quiz_id = r.json()["id"]
    check(r.json().get("quiz_type") == "poll", f"quiz_type should be poll, got {r.json().get('quiz_type')}")
    print(f"OK: create poll quiz  id={quiz_id}")

    # Add MCQ question (polls allow MCQ without correct answer)
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "Which session did you enjoy most?",
        "question_type": "mcq",
        "options": ["Morning keynote", "Workshop A", "Workshop B", "Panel discussion"],
        "max_time_seconds": 30,
    }, timeout=20)
    check(r.status_code in (200, 201), f"add MCQ question failed: {r.status_code} {r.text[:300]}")
    mcq_id = r.json()["id"]
    print(f"OK: add MCQ question  id={mcq_id}")

    # Add word_cloud question
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "What word best describes today's event?",
        "question_type": "word_cloud",
    }, timeout=20)
    check(r.status_code in (200, 201), f"add word_cloud question failed: {r.status_code} {r.text[:300]}")
    wc_id = r.json()["id"]
    print(f"OK: add word_cloud question  id={wc_id}")

    # Add scale question (5 options required)
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "How would you rate this session? (1=Poor, 5=Excellent)",
        "question_type": "scale",
        "options": ["1", "2", "3", "4", "5"],
    }, timeout=20)
    check(r.status_code in (200, 201), f"add scale question failed: {r.status_code} {r.text[:300]}")
    scale_id = r.json()["id"]
    print(f"OK: add scale question  id={scale_id}")

    # Verify quiz type and question count
    r = s.get(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)
    check(r.status_code == 200, f"get quiz failed: {r.status_code}")
    quiz_data = r.json()
    check(quiz_data.get("quiz_type") == "poll", f"quiz_type should still be poll, got {quiz_data.get('quiz_type')}")
    check(len(quiz_data.get("questions", [])) == 3, f"expected 3 questions, got {len(quiz_data.get('questions', []))}")
    print("OK: poll quiz has 3 questions, type=poll verified")

    # Publish
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/publish", timeout=20)
    check(r.status_code in (200, 201), f"publish failed: {r.status_code} {r.text[:200]}")
    print("OK: publish poll")

    # Start session
    r = s.post(f"{BASE_URL}/quizzes/sessions/start", params={"quiz_id": quiz_id}, timeout=20)
    check(r.status_code in (200, 201), f"start session failed: {r.status_code} {r.text[:200]}")
    session_id = r.json()["id"]
    join_code = r.json()["join_code"]
    print(f"OK: start session  id={session_id}  join_code={join_code}")

    # Two participants join (to verify multi-participant poll works)
    anon1 = requests.Session()
    anon1.verify = False
    r = anon1.post(f"{BASE_URL}/quizzes/sessions/join",
                   json={"join_code": join_code, "display_name": "PollParticipant1"}, timeout=20)
    check(r.status_code == 200, f"participant 1 join failed: {r.status_code} {r.text[:200]}")
    p_token1 = r.json()["session_token"]
    print(f"OK: participant 1 joined  token={p_token1[:12]}…")

    anon2 = requests.Session()
    anon2.verify = False
    r = anon2.post(f"{BASE_URL}/quizzes/sessions/join",
                   json={"join_code": join_code, "display_name": "PollParticipant2"}, timeout=20)
    check(r.status_code == 200, f"participant 2 join failed: {r.status_code} {r.text[:200]}")
    p_token2 = r.json()["session_token"]
    print(f"OK: participant 2 joined  token={p_token2[:12]}…")

    # ── MCQ question ──────────────────────────────────────────────────────────
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/advance", timeout=20)
    check(r.status_code in (200, 201), f"advance to MCQ failed: {r.status_code}")
    print("OK: advance to MCQ question")

    # Both participants answer MCQ
    r = anon1.post(f"{BASE_URL}/quizzes/sessions/submit-answer",
                   params={"session_token": p_token1},
                   json={"question_id": mcq_id, "selected_option_index": 0}, timeout=20)
    check(r.status_code in (200, 201), f"P1 MCQ answer failed: {r.status_code} {r.text[:200]}")

    r = anon2.post(f"{BASE_URL}/quizzes/sessions/submit-answer",
                   params={"session_token": p_token2},
                   json={"question_id": mcq_id, "selected_option_index": 2}, timeout=20)
    check(r.status_code in (200, 201), f"P2 MCQ answer failed: {r.status_code} {r.text[:200]}")
    print("OK: both participants answered MCQ")

    # ── word_cloud question ───────────────────────────────────────────────────
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/advance", timeout=20)
    check(r.status_code in (200, 201), f"advance to word_cloud failed: {r.status_code}")
    print("OK: advance to word_cloud question")

    r = anon1.post(f"{BASE_URL}/quizzes/sessions/submit-word-cloud",
                   params={"session_token": p_token1},
                   json={"question_id": wc_id, "text_answer": "innovative"}, timeout=20)
    check(r.status_code in (200, 201), f"P1 word_cloud answer failed: {r.status_code} {r.text[:200]}")

    r = anon2.post(f"{BASE_URL}/quizzes/sessions/submit-word-cloud",
                   params={"session_token": p_token2},
                   json={"question_id": wc_id, "text_answer": "innovative"}, timeout=20)
    check(r.status_code in (200, 201), f"P2 word_cloud answer failed: {r.status_code} {r.text[:200]}")
    print("OK: both participants answered word_cloud")

    # Word cloud aggregation for poll question
    r = s.get(f"{BASE_URL}/quizzes/questions/{wc_id}/word-cloud-results",
              params={"session_id": session_id}, timeout=20)
    check(r.status_code == 200, f"word_cloud results failed: {r.status_code} {r.text[:200]}")
    wc_data = r.json()
    check(wc_data.get("total_submissions", 0) >= 2, f"expected >=2 submissions, got {wc_data.get('total_submissions')}")
    print(f"OK: word_cloud results  submissions={wc_data.get('total_submissions')}")

    # ── scale question ────────────────────────────────────────────────────────
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/advance", timeout=20)
    check(r.status_code in (200, 201), f"advance to scale failed: {r.status_code}")
    print("OK: advance to scale question")

    # Submit scale answers (index 4 = "5", index 3 = "4")
    r = anon1.post(f"{BASE_URL}/quizzes/sessions/submit-answer",
                   params={"session_token": p_token1},
                   json={"question_id": scale_id, "selected_option_index": 4}, timeout=20)
    check(r.status_code in (200, 201), f"P1 scale answer failed: {r.status_code} {r.text[:200]}")

    r = anon2.post(f"{BASE_URL}/quizzes/sessions/submit-answer",
                   params={"session_token": p_token2},
                   json={"question_id": scale_id, "selected_option_index": 3}, timeout=20)
    check(r.status_code in (200, 201), f"P2 scale answer failed: {r.status_code} {r.text[:200]}")
    print("OK: both participants answered scale question")

    # Leaderboard: polls must return empty entries (no scoring)
    r = s.get(f"{BASE_URL}/quizzes/sessions/{session_id}/leaderboard", timeout=20)
    check(r.status_code == 200, f"leaderboard failed: {r.status_code}")
    lb = r.json()
    check(isinstance(lb.get("entries"), list), "leaderboard entries should be a list")
    check(len(lb.get("entries", [])) == 0, f"poll leaderboard must have 0 entries, got {len(lb.get('entries', []))}")
    check(lb.get("total_participants", 0) >= 2, f"expected >=2 participants, got {lb.get('total_participants')}")
    print(f"OK: poll leaderboard has 0 scored entries, {lb.get('total_participants')} participants")

    # End session
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/end", timeout=20)
    check(r.status_code in (200, 201), f"end session failed: {r.status_code}")
    print("OK: end session")

    # Verify results
    r = s.get(f"{BASE_URL}/quizzes/sessions/{session_id}/results", timeout=20)
    check(r.status_code == 200, f"results failed: {r.status_code}")
    results = r.json()
    check(results.get("quiz_type") == "poll", f"quiz_type in results should be poll, got {results.get('quiz_type')}")
    check(results.get("total_participants", 0) >= 2, f"expected >=2 participants in results")
    print(f"OK: session results  quiz_type={results.get('quiz_type')}  participants={results.get('total_participants')}")

    # Cleanup
    s.post(f"{BASE_URL}/quizzes/{quiz_id}/unpublish", timeout=20)
    s.delete(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)
    print("OK: cleanup (best-effort)")

    print("\nOK: live_poll_lifecycle — all steps passed")


if __name__ == "__main__":
    main()

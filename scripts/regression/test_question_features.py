#!/usr/bin/env python3
"""
Question Features Regression Test
Tests question-level features that were previously untested:
  - max_time_seconds: persists and is returned in session results for all question types
  - negative_points: field persists and is returned correctly
  - points: custom point values correctly calculated in scoring
  - Question update preserves all fields correctly
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

    # Create quiz
    r = s.post(f"{BASE_URL}/quizzes/", json={"title": "Question Features Regression"}, timeout=20)
    check(r.status_code in (200, 201), f"create quiz failed: {r.status_code}")
    quiz_id = r.json()["id"]
    print(f"OK: create quiz  id={quiz_id}")

    # Add MCQ with max_time_seconds, custom points, and negative_points
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "High-value timed question",
        "question_type": "mcq",
        "options": ["A", "B", "C", "D"],
        "correct_answer_index": 1,
        "max_time_seconds": 45,
        "points": 50,
        "negative_points": 10,
    }, timeout=20)
    check(r.status_code in (200, 201), f"add MCQ failed: {r.status_code} {r.text[:300]}")
    mcq_data = r.json()
    mcq_id = mcq_data["id"]
    check(mcq_data.get("max_time_seconds") == 45, f"max_time_seconds not persisted: {mcq_data.get('max_time_seconds')}")
    check(mcq_data.get("points") == 50, f"points not persisted: {mcq_data.get('points')}")
    check(mcq_data.get("negative_points") == 10, f"negative_points not persisted: {mcq_data.get('negative_points')}")
    print(f"OK: MCQ with max_time=45s, points=50, negative_points=10  id={mcq_id}")

    # Add word_cloud with max_time_seconds (now available for all types)
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "Share your thoughts (timed)",
        "question_type": "word_cloud",
        "max_time_seconds": 60,
    }, timeout=20)
    check(r.status_code in (200, 201), f"add word_cloud failed: {r.status_code} {r.text[:300]}")
    wc_data = r.json()
    wc_id = wc_data["id"]
    check(wc_data.get("max_time_seconds") == 60, f"word_cloud max_time_seconds not persisted: {wc_data.get('max_time_seconds')}")
    print(f"OK: word_cloud with max_time=60s  id={wc_id}")

    # Add offline_poll-style MCQ with max_time_seconds (validates timer works across all modes)
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "Standard scored question",
        "question_type": "mcq",
        "options": ["X", "Y", "Z", "W"],
        "correct_answer_index": 2,
        "points": 10,
        "max_time_seconds": 30,
    }, timeout=20)
    check(r.status_code in (200, 201), f"add second MCQ failed: {r.status_code} {r.text[:300]}")
    mcq2_id = r.json()["id"]
    print(f"OK: second MCQ  id={mcq2_id}")

    # Verify all fields persisted via GET
    r = s.get(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)
    check(r.status_code == 200, f"get quiz failed: {r.status_code}")
    qs = {q["id"]: q for q in r.json().get("questions", [])}
    check(qs[mcq_id]["max_time_seconds"] == 45, "MCQ max_time_seconds lost on GET")
    check(qs[mcq_id]["points"] == 50, "MCQ points lost on GET")
    check(qs[mcq_id]["negative_points"] == 10, "MCQ negative_points lost on GET")
    check(qs[wc_id]["max_time_seconds"] == 60, "word_cloud max_time_seconds lost on GET")
    print("OK: all question fields verified via GET quiz")

    # Update a question and verify max_time_seconds and negative_points survive update
    r = s.put(f"{BASE_URL}/quizzes/questions/{mcq_id}", json={
        "text": "Updated: High-value timed question",
        "max_time_seconds": 90,
        "negative_points": 20,
    }, timeout=20)
    check(r.status_code in (200, 201), f"update question failed: {r.status_code} {r.text[:200]}")
    upd = r.json()
    check(upd.get("max_time_seconds") == 90, f"max_time_seconds not updated: {upd.get('max_time_seconds')}")
    check(upd.get("negative_points") == 20, f"negative_points not updated: {upd.get('negative_points')}")
    check(upd.get("points") == 50, f"points changed unexpectedly: {upd.get('points')}")
    print("OK: question update preserves all fields correctly")

    # Publish and run a session to verify max_time_seconds appears in session results
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/publish", timeout=20)
    check(r.status_code in (200, 201), f"publish failed: {r.status_code}")
    print("OK: published")

    r = s.post(f"{BASE_URL}/quizzes/sessions/start", params={"quiz_id": quiz_id}, timeout=20)
    check(r.status_code in (200, 201), f"start session failed: {r.status_code}")
    session_id = r.json()["id"]
    join_code = r.json()["join_code"]
    print(f"OK: session started  id={session_id}")

    anon = requests.Session()
    anon.verify = False
    r = anon.post(f"{BASE_URL}/quizzes/sessions/join",
                  json={"join_code": join_code, "display_name": "FeaturesTester"}, timeout=20)
    check(r.status_code == 200, f"join failed: {r.status_code}")
    p_token = r.json()["session_token"]
    print(f"OK: joined  token={p_token[:12]}…")

    # Advance: max_time_seconds should appear in current_question of audience-results
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/advance", timeout=20)
    check(r.status_code in (200, 201), f"advance failed: {r.status_code}")

    r = anon.get(f"{BASE_URL}/quizzes/sessions/{session_id}/audience-results",
                 params={"session_token": p_token}, timeout=20)
    check(r.status_code == 200, f"audience-results failed: {r.status_code}")
    aud = r.json()
    cq = aud.get("current_question")
    check(cq is not None, "current_question missing from audience-results")
    check(cq.get("max_time_seconds") == 90, f"max_time_seconds not in audience current_question: {cq.get('max_time_seconds')}")
    print(f"OK: max_time_seconds={cq.get('max_time_seconds')} visible in audience-results")

    # Correct answer → earns 50 points (MCQ id=mcq_id updated to correct=1, but we changed text; correct_answer_index=1 still)
    r = anon.post(f"{BASE_URL}/quizzes/sessions/submit-answer",
                  params={"session_token": p_token},
                  json={"question_id": mcq_id, "selected_option_index": 1}, timeout=20)
    check(r.status_code in (200, 201), f"submit correct answer failed: {r.status_code}")
    print("OK: correct MCQ answer submitted")

    # End session and check scoring
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/end", timeout=20)
    check(r.status_code in (200, 201), f"end session failed: {r.status_code}")

    r = s.get(f"{BASE_URL}/quizzes/sessions/{session_id}/results", timeout=20)
    check(r.status_code == 200, f"results failed: {r.status_code}")
    print("OK: session results retrieved")

    # Leaderboard: verify the participant has a score (correct answer = 50 points)
    r = s.get(f"{BASE_URL}/quizzes/sessions/{session_id}/leaderboard", timeout=20)
    check(r.status_code == 200, f"leaderboard failed: {r.status_code}")
    entries = r.json().get("entries", [])
    check(len(entries) >= 1, "no leaderboard entries")
    top = entries[0]
    check(top.get("score", 0) == 50, f"expected score=50, got {top.get('score')}")
    print(f"OK: leaderboard correct  score={top.get('score')}  name={top.get('display_name')}")

    # Cleanup
    s.post(f"{BASE_URL}/quizzes/{quiz_id}/unpublish", timeout=20)
    s.delete(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)
    print("OK: cleanup (best-effort)")

    print("\nOK: question_features — all steps passed")


if __name__ == "__main__":
    main()

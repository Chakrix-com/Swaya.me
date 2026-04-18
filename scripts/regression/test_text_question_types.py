#!/usr/bin/env python3
"""
Text Question Types Regression Test
Tests all text-based question types end-to-end:
  - one_word: creation, valid single-word submission, rejection of multi-word
  - single_line: creation, text submission
  - paragraph: creation, text submission
Also verifies word-cloud results endpoint works for one_word questions.
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

    # Create a quiz (standard type — all question types are accepted by the API)
    r = s.post(f"{BASE_URL}/quizzes/", json={
        "title": "Text Question Types Regression",
        "description": "Regression test for one_word, single_line, paragraph",
    }, timeout=20)
    check(r.status_code in (200, 201), f"create quiz failed: {r.status_code} {r.text[:200]}")
    quiz_id = r.json()["id"]
    print(f"OK: create quiz  id={quiz_id}")

    # Add one_word question
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "Name a programming language in one word",
        "question_type": "one_word",
    }, timeout=20)
    check(r.status_code in (200, 201), f"add one_word question failed: {r.status_code} {r.text[:300]}")
    one_word_id = r.json()["id"]
    print(f"OK: add one_word question  id={one_word_id}")

    # Add single_line question (with optional expected answer as first option)
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "What is the capital of France?",
        "question_type": "single_line",
        "options": ["Paris"],
    }, timeout=20)
    check(r.status_code in (200, 201), f"add single_line question failed: {r.status_code} {r.text[:300]}")
    single_line_id = r.json()["id"]
    print(f"OK: add single_line question  id={single_line_id}")

    # Add paragraph question
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "Describe your experience with automated testing",
        "question_type": "paragraph",
    }, timeout=20)
    check(r.status_code in (200, 201), f"add paragraph question failed: {r.status_code} {r.text[:300]}")
    paragraph_id = r.json()["id"]
    print(f"OK: add paragraph question  id={paragraph_id}")

    # Verify all 3 questions saved with correct types
    r = s.get(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)
    check(r.status_code == 200, f"get quiz failed: {r.status_code}")
    questions = r.json().get("questions", [])
    check(len(questions) == 3, f"expected 3 questions, got {len(questions)}")
    qtypes = {q["id"]: q["question_type"] for q in questions}
    check(qtypes.get(one_word_id) == "one_word", f"one_word type mismatch: {qtypes.get(one_word_id)}")
    check(qtypes.get(single_line_id) == "single_line", f"single_line type mismatch: {qtypes.get(single_line_id)}")
    check(qtypes.get(paragraph_id) == "paragraph", f"paragraph type mismatch: {qtypes.get(paragraph_id)}")
    print("OK: all 3 question types persisted correctly")

    # Publish
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/publish", timeout=20)
    check(r.status_code in (200, 201), f"publish failed: {r.status_code} {r.text[:200]}")
    print("OK: publish")

    # Start session
    r = s.post(f"{BASE_URL}/quizzes/sessions/start", params={"quiz_id": quiz_id}, timeout=20)
    check(r.status_code in (200, 201), f"start session failed: {r.status_code} {r.text[:200]}")
    session_id = r.json()["id"]
    join_code = r.json()["join_code"]
    print(f"OK: start session  id={session_id}  join_code={join_code}")

    # Audience joins
    anon = requests.Session()
    anon.verify = False
    r = anon.post(f"{BASE_URL}/quizzes/sessions/join",
                  json={"join_code": join_code, "display_name": "TextTypesTester"}, timeout=20)
    check(r.status_code == 200, f"join failed: {r.status_code} {r.text[:200]}")
    p_token = r.json()["session_token"]
    print(f"OK: audience join  token={p_token[:12]}…")

    # ── one_word question ─────────────────────────────────────────────────────
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/advance", timeout=20)
    check(r.status_code in (200, 201), f"advance to one_word failed: {r.status_code}")
    print("OK: advance to one_word question")

    # Reject multi-word answer for one_word question
    r = anon.post(f"{BASE_URL}/quizzes/sessions/submit-word-cloud",
                  params={"session_token": p_token},
                  json={"question_id": one_word_id, "text_answer": "two words"},
                  timeout=20)
    check(r.status_code >= 400, f"multi-word answer should be rejected, got {r.status_code}: {r.text[:200]}")
    print(f"OK: multi-word one_word answer correctly rejected  status={r.status_code}")

    # Submit valid single-word answer
    r = anon.post(f"{BASE_URL}/quizzes/sessions/submit-word-cloud",
                  params={"session_token": p_token},
                  json={"question_id": one_word_id, "text_answer": "Python"},
                  timeout=20)
    check(r.status_code in (200, 201), f"one_word submit failed: {r.status_code} {r.text[:200]}")
    print("OK: one_word answer submitted")

    # Word cloud results for one_word question
    r = s.get(f"{BASE_URL}/quizzes/questions/{one_word_id}/word-cloud-results",
              params={"session_id": session_id}, timeout=20)
    check(r.status_code == 200, f"one_word results failed: {r.status_code} {r.text[:200]}")
    result_data = r.json()
    check("word_frequencies" in result_data, "word_frequencies missing from one_word results")
    check(result_data.get("total_submissions", 0) >= 1, "expected >=1 submission in one_word results")
    print(f"OK: one_word word-cloud results  submissions={result_data.get('total_submissions')}")

    # ── single_line question ──────────────────────────────────────────────────
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/advance", timeout=20)
    check(r.status_code in (200, 201), f"advance to single_line failed: {r.status_code}")
    print("OK: advance to single_line question")

    r = anon.post(f"{BASE_URL}/quizzes/sessions/submit-word-cloud",
                  params={"session_token": p_token},
                  json={"question_id": single_line_id, "text_answer": "Paris"},
                  timeout=20)
    check(r.status_code in (200, 201), f"single_line submit failed: {r.status_code} {r.text[:200]}")
    print("OK: single_line answer submitted")

    # ── paragraph question ────────────────────────────────────────────────────
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/advance", timeout=20)
    check(r.status_code in (200, 201), f"advance to paragraph failed: {r.status_code}")
    print("OK: advance to paragraph question")

    r = anon.post(f"{BASE_URL}/quizzes/sessions/submit-word-cloud",
                  params={"session_token": p_token},
                  json={"question_id": paragraph_id,
                        "text_answer": "Automated testing ensures code correctness and prevents regressions."},
                  timeout=20)
    check(r.status_code in (200, 201), f"paragraph submit failed: {r.status_code} {r.text[:200]}")
    print("OK: paragraph answer submitted")

    # End session and verify results
    r = s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/end", timeout=20)
    check(r.status_code in (200, 201), f"end session failed: {r.status_code}")
    print("OK: end session")

    r = s.get(f"{BASE_URL}/quizzes/sessions/{session_id}/results", timeout=20)
    check(r.status_code == 200, f"results failed: {r.status_code}")
    results = r.json()
    check(results.get("total_participants", 0) >= 1, "expected >=1 participant in results")
    print(f"OK: session results  participants={results.get('total_participants')}")

    # Cleanup
    s.post(f"{BASE_URL}/quizzes/{quiz_id}/unpublish", timeout=20)
    s.delete(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)
    print("OK: cleanup (best-effort)")

    print("\nOK: text_question_types — all steps passed")


if __name__ == "__main__":
    main()

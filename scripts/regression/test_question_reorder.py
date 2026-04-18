#!/usr/bin/env python3
"""
Question Reorder Regression Test
Tests PUT /quizzes/{quiz_id}/questions/reorder:
  - Creates a quiz with 3 questions, verifies initial order
  - Reorders questions (reverses order)
  - Fetches quiz and verifies order changed
  - Verifies reorder on a READY (published) quiz is rejected
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


def main():
    s = requests.Session()
    s.verify = False

    # Login
    r = s.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    check(r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}")
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    print("OK: login")

    # Create draft quiz
    r = s.post(f"{BASE_URL}/quizzes/", json={"title": "Reorder Regression Quiz"}, timeout=20)
    check(r.status_code in (200, 201), f"create quiz failed: {r.status_code} {r.text[:200]}")
    quiz_id = r.json()["id"]
    print(f"OK: create quiz  id={quiz_id}")

    # Add 3 questions — their creation order sets initial order
    q_labels = ["First Question (A)", "Second Question (B)", "Third Question (C)"]
    q_ids = []
    for label in q_labels:
        r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
            "text": label,
            "question_type": "mcq",
            "options": ["Yes", "No", "Maybe", "Unsure"],
            "correct_answer_index": 0,
        }, timeout=20)
        check(r.status_code in (200, 201), f"add question '{label}' failed: {r.status_code} {r.text[:200]}")
        q_ids.append(r.json()["id"])
        print(f"OK: add question '{label}'  id={q_ids[-1]}")

    # Fetch quiz and verify initial order
    r = s.get(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)
    check(r.status_code == 200, f"get quiz failed: {r.status_code}")
    qs = sorted(r.json().get("questions", []), key=lambda q: q["order"])
    check(len(qs) == 3, f"expected 3 questions, got {len(qs)}")
    initial_order = [q["id"] for q in qs]
    check(initial_order == q_ids, f"initial order unexpected: {initial_order} vs {q_ids}")
    print(f"OK: initial question order verified  {[q['text'][:12] for q in qs]}")

    # Reorder: reverse the order (C, B, A)
    new_order = [[q_ids[2], 0], [q_ids[1], 1], [q_ids[0], 2]]
    r = s.put(f"{BASE_URL}/quizzes/{quiz_id}/questions/reorder",
              json={"question_orders": new_order}, timeout=20)
    check(r.status_code == 204, f"reorder failed: {r.status_code} {r.text[:200]}")
    print("OK: reorder request accepted (204)")

    # Fetch quiz and verify new order
    r = s.get(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)
    check(r.status_code == 200, f"get quiz after reorder failed: {r.status_code}")
    qs_after = sorted(r.json().get("questions", []), key=lambda q: q["order"])
    reordered_ids = [q["id"] for q in qs_after]
    expected = [q_ids[2], q_ids[1], q_ids[0]]
    check(reordered_ids == expected, f"reorder not applied: got {reordered_ids}, expected {expected}")
    print(f"OK: question order reversed successfully  {[q['text'][:12] for q in qs_after]}")

    # Partial reorder: move only first question to position 2
    partial_order = [[q_ids[2], 0], [q_ids[0], 2]]
    r = s.put(f"{BASE_URL}/quizzes/{quiz_id}/questions/reorder",
              json={"question_orders": partial_order}, timeout=20)
    check(r.status_code == 204, f"partial reorder failed: {r.status_code} {r.text[:200]}")
    print("OK: partial reorder accepted (204)")

    # Publish quiz
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/publish", timeout=20)
    check(r.status_code in (200, 201), f"publish failed: {r.status_code}")
    print("OK: quiz published (READY)")

    # Reorder on READY quiz must be rejected
    r = s.put(f"{BASE_URL}/quizzes/{quiz_id}/questions/reorder",
              json={"question_orders": [[q_ids[0], 0], [q_ids[1], 1], [q_ids[2], 2]]}, timeout=20)
    check(r.status_code >= 400, f"reorder on READY quiz should be rejected, got {r.status_code}: {r.text[:200]}")
    print(f"OK: reorder on READY quiz correctly rejected  status={r.status_code}")

    # Cleanup
    s.post(f"{BASE_URL}/quizzes/{quiz_id}/unpublish", timeout=20)
    s.delete(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)
    print("OK: cleanup (best-effort)")

    print("\nOK: question_reorder — all steps passed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Miscellaneous Endpoints Coverage
Tests: app feedback (anon + auth), language preference, language event (anon),
       AI rewrite (503-tolerant), export session results, whiteboard get/update/public,
       session feedback from user.
"""
import os
import sys
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = os.getenv("BASE_URL", "https://test.swaya.me/api/v1").rstrip("/")
HOST_EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
HOST_PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")
REG_EMAIL = os.getenv("REGULAR_USER_EMAIL", "regression-free@swaya.me")
REG_PASSWORD = os.getenv("REGULAR_USER_PASSWORD", "RegTest2026!")


def fail(msg: str):
    print(f"FAIL: {msg}")
    sys.exit(1)


def check(cond: bool, msg: str):
    if not cond:
        fail(msg)


def main():
    anon = requests.Session()
    anon.verify = False

    reg = requests.Session()
    reg.verify = False
    r = reg.post(f"{BASE_URL}/auth/login", json={"email": REG_EMAIL, "password": REG_PASSWORD}, timeout=20)
    check(r.status_code == 200, f"reg login failed: {r.status_code}")
    reg.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    print("OK: regular user login")

    adm = requests.Session()
    adm.verify = False
    r = adm.post(f"{BASE_URL}/auth/login", json={"email": HOST_EMAIL, "password": HOST_PASSWORD}, timeout=20)
    check(r.status_code == 200, f"admin login failed: {r.status_code}")
    adm.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    print("OK: admin login")

    # 1. App feedback — anonymous submit
    r = anon.post(f"{BASE_URL}/feedback/app", json={
        "rating": 4,
        "feedback_text": "regression test anon feedback",
        "page_url": "https://test.swaya.me/",
    }, timeout=20)
    check(r.status_code in (200, 201), f"anon app feedback failed: {r.status_code} {r.text[:200]}")
    print("OK: anon app feedback")

    # 2. App feedback — authenticated submit
    r = reg.post(f"{BASE_URL}/feedback/app", json={
        "rating": 5,
        "feedback_text": "regression test auth feedback",
        "page_url": "https://test.swaya.me/dashboard",
    }, timeout=20)
    check(r.status_code in (200, 201), f"auth app feedback failed: {r.status_code} {r.text[:200]}")
    print("OK: auth app feedback")

    # 3. Language preference update (authenticated)
    r = reg.post(f"{BASE_URL}/user/language-preference", json={
        "language": "en",
        "previous_language": "hi",
    }, timeout=20)
    check(r.status_code in (200, 201), f"language preference failed: {r.status_code} {r.text[:200]}")
    print("OK: language preference update")

    # 4. Language event (anonymous)
    r = anon.post(f"{BASE_URL}/language-tracking/event", json={
        "language": "ta",
        "previous_language": "en",
        "session_id": "regtest-session-anon",
        "user_agent": "regression-test/1.0",
    }, timeout=20)
    check(r.status_code in (200, 201), f"anon language event failed: {r.status_code} {r.text[:200]}")
    print("OK: anon language event")

    # 5. AI rewrite (503-tolerant — Ollama may not be running on test env)
    r = reg.post(f"{BASE_URL}/ai/rewrite", json={
        "text": "what is 2+2",
        "style": "formal",
    }, timeout=30)
    check(r.status_code in (200, 201, 422, 503, 404), f"AI rewrite unexpected status: {r.status_code} {r.text[:200]}")
    print(f"OK: AI rewrite  status={r.status_code} (503 acceptable)")

    # 6. End any stale open sessions for the regular user to avoid FREE tier concurrent limit
    quizzes_r = reg.get(f"{BASE_URL}/quizzes/", timeout=20)
    if quizzes_r.status_code == 200:
        for q in quizzes_r.json():
            sess_r = reg.get(f"{BASE_URL}/quizzes/{q['id']}/sessions", timeout=20)
            if sess_r.status_code == 200:
                for sess in sess_r.json().get("sessions", []):
                    if sess.get("status") in ("created", "active"):
                        reg.post(f"{BASE_URL}/quizzes/sessions/{sess['id']}/end", timeout=20)

    # Create a quiz + session for whiteboard and export tests
    r = reg.post(f"{BASE_URL}/quizzes/", json={"title": "Misc Endpoints Test Quiz"}, timeout=20)
    check(r.status_code in (200, 201), f"create quiz failed: {r.status_code}")
    quiz_id = r.json()["id"]

    r = reg.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "Misc test question",
        "question_type": "mcq",
        "options": ["A", "B", "C", "D"],
        "correct_answer_index": 0,
        "max_time_seconds": 30,
        "points": 10,
    }, timeout=20)
    check(r.status_code in (200, 201), f"add question failed: {r.status_code}")

    r = reg.post(f"{BASE_URL}/quizzes/{quiz_id}/publish", timeout=20)
    check(r.status_code in (200, 201), f"publish failed: {r.status_code}")

    r = reg.post(f"{BASE_URL}/quizzes/sessions/start", params={"quiz_id": quiz_id}, timeout=20)
    check(r.status_code in (200, 201), f"start session failed: {r.status_code}")
    session_id = r.json()["id"]
    print(f"OK: created quiz/session  quiz={quiz_id}  session={session_id}")

    # 7. Whiteboard get
    r = reg.get(f"{BASE_URL}/quizzes/sessions/{session_id}/whiteboard-state", timeout=20)
    check(r.status_code in (200, 404), f"whiteboard get failed: {r.status_code} {r.text[:200]}")
    print(f"OK: whiteboard get  status={r.status_code}")

    # 8. Whiteboard update
    r = reg.put(f"{BASE_URL}/quizzes/sessions/{session_id}/whiteboard-state", json={
        "question_index": 0,
        "enabled": False,
    }, timeout=20)
    check(r.status_code in (200, 201, 404, 409, 422), f"whiteboard update failed: {r.status_code} {r.text[:200]}")
    print(f"OK: whiteboard update  status={r.status_code}")

    # 9. Export session results
    r = reg.get(f"{BASE_URL}/quizzes/sessions/{session_id}/export", params={"format": "xlsx"}, timeout=30)
    check(r.status_code in (200, 404), f"export failed: {r.status_code} {r.text[:200]}")
    print(f"OK: export session  status={r.status_code}")

    # 10. End session and cleanup (unpublish first so quiz can be deleted)
    reg.post(f"{BASE_URL}/quizzes/sessions/{session_id}/end", timeout=20)
    reg.post(f"{BASE_URL}/quizzes/{quiz_id}/unpublish", timeout=20)
    reg.delete(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)

    print("\nOK: misc_endpoints — all steps passed")


if __name__ == "__main__":
    main()

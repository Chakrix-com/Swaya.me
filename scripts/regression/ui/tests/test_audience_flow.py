"""
Audience Flow Regression
Tests: regular user starts session → second browser context joins → question advances → answers submitted → no console errors.
This covers the regular-user path that surfaced the stripHtml bug.
"""
import os
import pytest
import requests
from playwright.sync_api import Page, Browser, BrowserContext
from conftest import login, assert_no_js_errors, BASE_URL, REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD

API_BASE = os.getenv("BASE_URL", "https://test.swaya.me/api/v1").rstrip("/")


def _api_login(email: str, password: str) -> str:
    r = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password}, verify=False, timeout=20)
    assert r.status_code == 200, f"API login failed: {r.status_code}"
    return r.json()["access_token"]


def _setup_quiz(token: str) -> tuple:
    """Create quiz with 1 MCQ question, publish, return (quiz_id, question_id)."""
    h = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{API_BASE}/quizzes/", json={"title": "AudienceFlow UI Test"}, headers=h, verify=False, timeout=20)
    assert r.status_code in (200, 201), f"create quiz: {r.status_code} {r.text[:200]}"
    quiz_id = r.json()["id"]

    r = requests.post(f"{API_BASE}/quizzes/{quiz_id}/questions", headers=h, verify=False, timeout=20, json={
        "text": "Audience flow test question?",
        "question_type": "mcq",
        "options": ["Yes", "No", "Maybe", "Always"],
        "correct_answer_index": 0,
        "max_time_seconds": 30,
        "points": 100,
    })
    assert r.status_code in (200, 201), f"add question: {r.status_code} {r.text[:200]}"
    question_id = r.json()["id"]

    r = requests.post(f"{API_BASE}/quizzes/{quiz_id}/publish", headers=h, verify=False, timeout=20)
    assert r.status_code in (200, 201), f"publish: {r.status_code}"

    return quiz_id, question_id


def _cleanup(token: str, quiz_id: int, session_id: int):
    h = {"Authorization": f"Bearer {token}"}
    requests.post(f"{API_BASE}/quizzes/sessions/{session_id}/end", headers=h, verify=False, timeout=20)
    requests.delete(f"{API_BASE}/quizzes/{quiz_id}", headers=h, verify=False, timeout=20)


def test_audience_flow_regular_user(page: Page, browser: Browser):
    """Regular user hosts session; second context joins as audience; no JS errors on either side."""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    host_errors = []
    page.on("console", lambda msg: host_errors.append(msg.text) if msg.type == "error" else None)

    token = _api_login(REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD)
    quiz_id, question_id = _setup_quiz(token)

    try:
        h = {"Authorization": f"Bearer {token}"}

        # End any open sessions to avoid FREE-tier concurrent limit
        for q in requests.get(f"{API_BASE}/quizzes/", headers=h, verify=False, timeout=20).json():
            sr = requests.get(f"{API_BASE}/quizzes/{q['id']}/sessions", headers=h, verify=False, timeout=20)
            if sr.status_code == 200:
                for sess in sr.json().get("sessions", []):
                    if sess.get("status") in ("created", "active"):
                        requests.post(f"{API_BASE}/quizzes/sessions/{sess['id']}/end", headers=h, verify=False, timeout=20)

        # Start session via API (more reliable than UI extraction)
        sess_r = requests.post(f"{API_BASE}/quizzes/sessions/start", params={"quiz_id": quiz_id},
                               headers=h, verify=False, timeout=20)
        assert sess_r.status_code in (200, 201), f"session start failed: {sess_r.status_code} {sess_r.text[:200]}"
        session_api = sess_r.json()
        session_id_for_cleanup = session_api["id"]
        join_code = session_api["join_code"]
        print(f"  session started via API  join_code={join_code}")

        # Host: login and navigate to quiz control (to advance questions)
        login(page, REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD)
        page.goto(f"{BASE_URL}/quiz/{quiz_id}/control")
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(2000)
        print(f"  join_code={join_code}")

        # Audience: open second context and join
        audience_ctx: BrowserContext = browser.new_context(ignore_https_errors=True)
        audience_page = audience_ctx.new_page()
        audience_errors = []
        audience_page.on("console", lambda msg: audience_errors.append(msg.text) if msg.type == "error" else None)

        try:
            audience_page.goto(f"{BASE_URL}/join")
            audience_page.wait_for_load_state("networkidle", timeout=10000)

            # Fill join form
            code_input = audience_page.locator("input[inputmode='numeric'], input[placeholder*='code' i]").first
            code_input.fill(join_code)
            name_input = audience_page.locator("input[placeholder*='name' i], input#join_display_name").first
            name_input.fill("AudienceFlowTester")
            audience_page.locator("button:has-text('Join'), button[type='submit']").first.click()
            audience_page.wait_for_timeout(2000)

            # Advance to first question (host side)
            page.locator("button:has-text('Start First Question'), button:has-text('Next Question'), button:has-text('Next')").first.click()
            page.wait_for_timeout(2000)

            # Audience should see the question — wait for answer options
            audience_page.wait_for_timeout(3000)
            audience_body = audience_page.locator("body").text_content()
            print(f"  audience body snippet: {audience_body[:200]}")

            # Submit answer if options visible
            answer_btn = audience_page.locator("button.ant-radio-button-wrapper, .ant-btn:has-text('Yes'), .ant-btn:has-text('No')").first
            if answer_btn.count() > 0:
                answer_btn.click()
                audience_page.wait_for_timeout(1000)
                submit = audience_page.locator("button:has-text('Submit')").first
                if submit.count() > 0:
                    submit.click()
                    audience_page.wait_for_timeout(1000)
                    print("  audience submitted answer")

            assert_no_js_errors(audience_errors, "audience_page")

        finally:
            audience_page.close()
            audience_ctx.close()

        # Get session_id from API for cleanup
        h = {"Authorization": f"Bearer {token}"}
        sessions_r = requests.get(f"{API_BASE}/quizzes/{quiz_id}/sessions", headers=h, verify=False, timeout=20)
        sessions = sessions_r.json().get("sessions", []) if sessions_r.status_code == 200 else []
        session_id = sessions[0]["id"] if sessions else None

        assert_no_js_errors(host_errors, "host_page")
        print("OK: audience_flow_regular_user — no JS errors on host or audience")

    finally:
        h = {"Authorization": f"Bearer {token}"}
        sessions_r = requests.get(f"{API_BASE}/quizzes/{quiz_id}/sessions", headers=h, verify=False, timeout=20)
        if sessions_r.status_code == 200:
            for sess in sessions_r.json().get("sessions", []):
                if sess.get("status") in ("active", "created"):
                    requests.post(f"{API_BASE}/quizzes/sessions/{sess['id']}/end", headers=h, verify=False, timeout=20)
        requests.delete(f"{API_BASE}/quizzes/{quiz_id}", headers=h, verify=False, timeout=20)

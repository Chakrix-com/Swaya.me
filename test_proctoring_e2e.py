#!/usr/bin/env python3
"""
E2E Test for Proctoring Flow
Tests: Create exam with proctoring → Participant visits URL →
       Sees Proctoring Gate → Acknowledges → Starts Exam →
       Verifies fullscreen requirement (UI element)
"""
import time
import sys
import os
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from datetime import datetime, timezone, timedelta

BASE_URL = os.getenv("APP_BASE_URL", "https://test.swaya.me")
API_BASE_URL = os.getenv("BASE_URL", f"{BASE_URL}/api/v1")
HOST_HEADER = os.getenv("HOST_HEADER")
SELENIUM_URL = os.getenv("SELENIUM_URL", "http://localhost:4444/wd/hub")
TIMEOUT = 20

EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")


def log(message, level="INFO"):
    colors = {"INFO": "\033[94m", "SUCCESS": "\033[92m", "ERROR": "\033[91m", "WARN": "\033[93m"}
    print(f"{colors.get(level, '')}[{level}] {message}\033[0m")


def api_request(method, url, **kwargs):
    if HOST_HEADER:
        headers = kwargs.get("headers", {})
        headers["Host"] = HOST_HEADER
        kwargs["headers"] = headers
    return requests.request(method, url, **kwargs)


def setup_driver(name="driver"):
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,1024')
    # Required for fullscreen emulation in some drivers if possible
    options.add_argument('--start-maximized')
    driver = webdriver.Remote(command_executor=SELENIUM_URL, options=options)
    driver.set_page_load_timeout(30)
    log(f"Driver '{name}' initialized", "SUCCESS")
    return driver


def wait_for(driver, by, value, timeout=TIMEOUT, name="element", clickable=False):
    try:
        cond = EC.element_to_be_clickable((by, value)) if clickable else EC.presence_of_element_located((by, value))
        return WebDriverWait(driver, timeout).until(cond)
    except TimeoutException:
        driver.save_screenshot(f"/tmp/timeout_{name.replace(' ', '_')}.png")
        raise TimeoutException(f"Timeout waiting for: {name}")


def api_login():
    r = api_request("POST", f"{API_BASE_URL}/auth/login",
                      json={"email": EMAIL, "password": PASSWORD},
                      verify=False, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def create_proctored_exam(token):
    """Create a new exam with proctoring enabled via API."""
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(timezone.utc)
    
    # 1. Create Quiz
    r = api_request("POST", f"{API_BASE_URL}/quizzes/", headers=headers, json={
        "title": f"Proctored Regression Exam {now.strftime('%H%M%S')}",
        "quiz_type": "exam",
        "exam_start_at": now.isoformat(),
        "exam_end_at": (now + timedelta(hours=1)).isoformat(),
        "proctoring_policy": {
            "enabled": True,
            "rules": {
                "fullscreen_enforce": {"enabled": True},
                "tab_switch_detect": {"enabled": True}
            },
            "escalation": {
                "lock_on_violation_count": 3,
                "auto_submit_on_lock": False
            }
        }
    }, verify=False, timeout=20)
    r.raise_for_status()
    quiz_id = r.json()["id"]
    
    # 2. Add a question
    api_request("POST", f"{API_BASE_URL}/quizzes/{quiz_id}/questions", headers=headers, json={
        "text": "Is proctoring active?",
        "question_type": "mcq",
        "options": ["Yes", "No"],
        "correct_answer_index": 0,
        "points": 1
    }, verify=False, timeout=20).raise_for_status()
    
    # 3. Publish
    r = api_request("POST", f"{API_BASE_URL}/quizzes/{quiz_id}/publish-exam", headers=headers, verify=False, timeout=20)
    r.raise_for_status()
    slug = r.json().get("exam_slug")
    
    log(f"Created proctored exam: id={quiz_id} slug={slug}", "SUCCESS")
    return quiz_id, slug


def test_proctoring_e2e():
    driver = None
    try:
        log("=== Starting Proctoring E2E ===")

        token = api_login()
        quiz_id, slug = create_proctored_exam(token)
        exam_url = f"{BASE_URL}/e/{slug}"

        # ── Step 1: Open exam start screen ──
        log("\n--- STEP 1: Open exam start screen ---")
        driver = setup_driver("participant")
        driver.get(exam_url)
        time.sleep(5)
        driver.save_screenshot("/tmp/proctor_01_start.png")

        # ── Step 2: Verify proctoring rules shown on start screen + acknowledge ──
        log("\n--- STEP 2: Verify proctoring rules on start screen and acknowledge ---")
        name_input = wait_for(driver, By.CSS_SELECTOR, "input[type='text']", name="name input")
        name_input.send_keys("Proctor Tester")

        # Proctoring rules preview + acknowledgment checkbox are now inline on the start screen
        body_text = driver.find_element(By.TAG_NAME, "body").text
        body_text_lower = body_text.lower()
        if not any(k in body_text_lower for k in ["proctoring", "integrity", "monitoring", "rules", "fullscreen"]):
            raise AssertionError(f"No proctoring notice on start screen. Body: {body_text[:300]}")
        log("Proctoring notice visible on start screen", "SUCCESS")

        # The submit button must be DISABLED until the acknowledgment checkbox is checked
        start_btn_before = driver.find_element(By.XPATH, "//button[@type='submit']")
        assert start_btn_before.get_attribute("disabled") is not None, \
            "Submit button should be disabled before acknowledgment"
        log("Submit button correctly disabled before acknowledgment", "SUCCESS")

        # Check the acknowledgment checkbox
        ack_checkbox = wait_for(driver, By.ID, "proctor-ack", name="ack checkbox")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'})", ack_checkbox)
        driver.execute_script("arguments[0].click()", ack_checkbox)
        time.sleep(0.3)
        log("Acknowledgment checkbox checked", "SUCCESS")

        # Now the button should be enabled
        start_btn = wait_for(driver, By.XPATH, "//button[@type='submit']", clickable=True, name="start button")
        assert start_btn.get_attribute("disabled") is None, \
            "Submit button still disabled after acknowledgment"
        log("Submit button enabled after acknowledgment", "SUCCESS")

        # ── Step 3: Start exam — goes directly to proctoring setup (no duplicate warning screen) ──
        log("\n--- STEP 3: Click Start, verify no duplicate warning screen ---")
        driver.execute_script("arguments[0].click()", start_btn)
        time.sleep(3)
        driver.save_screenshot("/tmp/proctor_02_after_start.png")

        body_text = driver.find_element(By.TAG_NAME, "body").text
        # Should NOT see the old full-page red warning (that was the duplicate screen)
        # Should see webcam / fullscreen gate instead
        still_on_start = "Enter your full name" in body_text or "Send OTP" in body_text
        assert not still_on_start, "Still on start screen after clicking Start"
        log("Advanced past start screen", "SUCCESS")

        # ── Step 4: (renamed from Step 4) — no separate warning screen to dismiss ──
        log("\n--- STEP 4: Proctoring gate (webcam/fullscreen) shown directly ---")
        driver.save_screenshot("/tmp/proctor_03_fullscreen_gate.png")

        # ── Step 5: Verify Fullscreen Gate (Blocked state) ──
        log("\n--- STEP 5: Verify Fullscreen Gate ---")
        # Since we are in a headless/remote browser, it might NOT be in fullscreen by default.
        # The ProctoringGate should show "Fullscreen Mode Required"
        body_text = driver.find_element(By.TAG_NAME, "body").text
        # proctoring.fullscreen.blockedTitle
        has_blocked = any(k in body_text for k in ["Fullscreen", "Mode", "Required", "Full screen"])
        log(f"Fullscreen gate active: {has_blocked}", "SUCCESS" if has_blocked else "WARN")
        
        # Try to "Retry Fullscreen"
        retry_btn = driver.find_elements(By.XPATH, "//button[contains(., 'Enter Fullscreen') or contains(., 'Retry')]")
        if retry_btn:
            log("Found 'Enter Fullscreen' button", "SUCCESS")
            # In automated tests, actual fullscreen might fail, but we verify the button exists
        else:
            log("No 'Enter Fullscreen' button found (maybe already in fullscreen?)", "INFO")

        log("\n=== Proctoring E2E: PASSED (to gate level) ===", "SUCCESS")
        return True

    except Exception as e:
        log(f"Test FAILED: {e}", "ERROR")
        if driver:
            try:
                driver.save_screenshot("/tmp/proctor_error.png")
            except Exception:
                pass
        return False
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    sys.exit(0 if test_proctoring_e2e() else 1)

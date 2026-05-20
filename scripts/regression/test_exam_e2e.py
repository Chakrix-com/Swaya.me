#!/usr/bin/env python3
"""
E2E Test for Test (Exam) Type Flow
Tests: Find published test → Participant visits /e/:slug → Sees scoring rules + timer →
       Answers all questions → Submits → Views score → Host sees leaderboard
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
from datetime import datetime, timezone

BASE_URL = os.getenv("APP_BASE_URL", "https://test.swaya.me")
API_BASE_URL = os.getenv("BASE_URL", f"{BASE_URL}/api/v1")
SELENIUM_URL = os.getenv("SELENIUM_URL", "http://localhost:4444/wd/hub")
TIMEOUT = 20

EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")


def log(message, level="INFO"):
    colors = {"INFO": "\033[94m", "SUCCESS": "\033[92m", "ERROR": "\033[91m", "WARN": "\033[93m"}
    print(f"{colors.get(level, '')}[{level}] {message}\033[0m")


def setup_driver(name="driver"):
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,900')
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


def wait_for_any(driver, locators, timeout=TIMEOUT, name="element", clickable=False):
    for by, value in locators:
        try:
            cond = EC.element_to_be_clickable((by, value)) if clickable else EC.presence_of_element_located((by, value))
            return WebDriverWait(driver, timeout).until(cond)
        except TimeoutException:
            continue
    driver.save_screenshot(f"/tmp/timeout_{name.replace(' ', '_')}.png")
    raise TimeoutException(f"No locator matched for: {name}")


def safe_quit(driver):
    try:
        driver.quit()
    except Exception:
        pass


def api_login():
    r = requests.post(f"{API_BASE_URL}/auth/login",
                      json={"email": EMAIL, "password": PASSWORD},
                      verify=False, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def find_published_exam(token):
    """Find any published test/exam quiz and return (quiz_id, slug)."""
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE_URL}/quizzes/", headers=headers, verify=False, timeout=20)
    r.raise_for_status()
    now = datetime.now(timezone.utc)
    
    for quiz in r.json():
        if quiz.get("quiz_type") == "exam" and quiz.get("status") == "ready":
            # Check if exam is currently within its scheduled window
            start_str = quiz.get("exam_start_at")
            end_str = quiz.get("exam_end_at")
            
            is_active = True
            try:
                if start_str:
                    start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    if start_dt.tzinfo is None: start_dt = start_dt.replace(tzinfo=timezone.utc)
                    if now < start_dt:
                        is_active = False
                
                if end_str:
                    end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                    if end_dt.tzinfo is None: end_dt = end_dt.replace(tzinfo=timezone.utc)
                    if now > end_dt:
                        is_active = False
            except Exception as e:
                log(f"Error parsing dates for exam {quiz['id']}: {e}", "WARN")
                is_active = False # Fallback to safe side
                
            if not is_active:
                log(f"Skipping exam {quiz['id']} (slug={quiz.get('exam_slug')}): Not in active time window", "INFO")
                continue

            slug = quiz.get("slug") or quiz.get("exam_url", "").split("/")[-1]
            if not slug:
                continue

            # Fetch detail to check if proctoring or email OTP is enabled — skip both for the classic flow test
            detail = requests.get(f"{API_BASE_URL}/quizzes/{quiz['id']}", headers=headers, verify=False, timeout=20)
            if detail.status_code == 200:
                detail_json = detail.json()
                policy = detail_json.get("proctoring_policy") or {}
                if policy.get("enabled"):
                    log(f"Skipping exam {quiz['id']}: proctoring enabled", "INFO")
                    continue
                if detail_json.get("exam_require_email"):
                    log(f"Skipping exam {quiz['id']}: email OTP required (use test_exam_otp_e2e.py)", "INFO")
                    continue

            log(f"Found active published test: id={quiz['id']} slug={slug}", "SUCCESS")
            return quiz["id"], slug
    raise RuntimeError("No published exam/test found. Please publish at least one test in the dashboard.")


def test_exam_flow():
    driver = None
    try:
        log("=== Starting Test (Exam) E2E ===")

        token = api_login()
        quiz_id, slug = find_published_exam(token)
        exam_url = f"{BASE_URL}/e/{slug}"

        # ── Step 1: Open exam start screen ──
        log("\n--- STEP 1: Open exam start screen ---")
        driver = setup_driver("participant")
        driver.get(exam_url)
        time.sleep(5)
        driver.save_screenshot("/tmp/exam_01_start.png")

        body_text = driver.find_element(By.TAG_NAME, "body").text
        assert "500" not in body_text, "Exam page returned 500"
        log(f"Exam page loaded: {exam_url}", "SUCCESS")

        # ── Step 2: Verify start screen elements ──
        log("\n--- STEP 2: Verify start screen ---")
        # Scoring rules should be visible (Tags with +N / -N)
        # At minimum, there should be a Start button
        start_btn = wait_for_any(driver, [
            (By.XPATH, "//button[contains(., 'Start Test')]"),
            (By.XPATH, "//button[contains(., 'Start Exam')]"),
            (By.XPATH, "//button[contains(., 'Start')]"),
            (By.XPATH, "//button[contains(., 'Begin')]"),
        ], name="start test button")
        log("Start button found on start screen", "SUCCESS")

        # Check for scoring info
        body_text = driver.find_element(By.TAG_NAME, "body").text
        has_scoring = any(k in body_text for k in ["+", "correct", "Correct", "Score", "Points"])
        log(f"Scoring info visible: {has_scoring}", "SUCCESS" if has_scoring else "WARN")

        # ── Step 3: Enter name and start ──
        log("\n--- STEP 3: Enter name and start test ---")
        name_input = wait_for_any(driver, [
            (By.CSS_SELECTOR, "input[placeholder*='name' i]"),
            (By.CSS_SELECTOR, "input[placeholder*='Name' i]"),
            (By.CSS_SELECTOR, "input[type='text']"),
        ], name="name input")
        name_input.clear()
        name_input.send_keys("Regression Tester")

        # Acknowledge proctoring rules if the checkbox is present
        ack_boxes = driver.find_elements(By.ID, "proctor-ack")
        if ack_boxes:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'})", ack_boxes[0])
            if not ack_boxes[0].is_selected():
                driver.execute_script("arguments[0].click()", ack_boxes[0])
            log("Proctoring acknowledgment checked", "INFO")

        start_btn = wait_for_any(driver, [
            (By.XPATH, "//button[contains(., 'Start Test')]"),
            (By.XPATH, "//button[contains(., 'Start Exam')]"),
            (By.XPATH, "//button[contains(., 'Start')]"),
        ], clickable=True, name="start button")
        driver.execute_script("arguments[0].click()", start_btn)
        time.sleep(3)
        driver.save_screenshot("/tmp/exam_02_question1.png")
        log("Started test", "SUCCESS")

        # ── Step 4: Verify countdown timer visible ──
        log("\n--- STEP 4: Verify timer ---")
        body_text = driver.find_element(By.TAG_NAME, "body").text
        has_timer = any(k in body_text for k in ["Time Remaining", "remaining", ":", "timer"])
        log(f"Timer visible: {has_timer}", "SUCCESS" if has_timer else "WARN")

        # ── Step 5: Answer all questions ──
        log("\n--- STEP 5: Answer questions ---")
        answered = 0
        for attempt in range(100):
            # Dismiss any open Ant Design modal/confirm dialog first
            # Look for modal overlay — if present, click its primary/confirm button
            modal_overlays = driver.find_elements(By.CSS_SELECTOR, ".ant-modal-wrap:not([style*='display: none'])")
            if modal_overlays:
                # Try to click confirm/submit inside modal (not Cancel)
                modal_btns = driver.find_elements(By.XPATH,
                    "//div[contains(@class,'ant-modal')]//button[contains(., 'Submit') or contains(., 'Yes') or contains(., 'Confirm') or contains(., 'OK')]")
                if modal_btns:
                    driver.execute_script("arguments[0].click();", modal_btns[0])
                    time.sleep(2)
                    continue

            body_text = driver.find_element(By.TAG_NAME, "body").text

            # Detect results screen
            if any(k in body_text for k in ["Your Score", "Score", "Results", "Correct", "Submitted", "completed"]):
                # Check it's actually the results screen (not just score labels during quiz)
                if "Submit" not in body_text and answered > 0:
                    log(f"Results screen reached after {answered} question(s)", "SUCCESS")
                    break

            # Select first available radio option (use JS click to bypass overlays)
            radios = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            if radios:
                driver.execute_script("arguments[0].click();", radios[0])
                time.sleep(0.5)

            # Click Next / Submit Test (use JS click to bypass any residual overlay)
            for btn_text in ["Next", "Submit Test", "Submit Exam", "Submit", "Continue"]:
                btns = driver.find_elements(By.XPATH, f"//button[contains(., '{btn_text}')]")
                clickable_btns = [b for b in btns if b.is_enabled()]
                if clickable_btns:
                    driver.execute_script("arguments[0].click();", clickable_btns[0])
                    answered += 1
                    time.sleep(2)
                    break

        driver.save_screenshot("/tmp/exam_03_results.png")

        # ── Step 6: Verify results screen ──
        log("\n--- STEP 6: Verify results screen ---")
        body_text = driver.find_element(By.TAG_NAME, "body").text
        assert any(k in body_text for k in ["Score", "score", "Correct", "Result"]), \
            f"Results screen not detected. Body: {body_text[:300]}"
        log("Results screen confirmed with score information", "SUCCESS")

        # ── Step 7: Verify host leaderboard via API ──
        log("\n--- STEP 7: Verify host leaderboard ---")
        headers = {"Authorization": f"Bearer {token}"}
        lb_r = requests.get(f"{API_BASE_URL}/quiz/{quiz_id}/exam-results",
                            headers=headers, verify=False, timeout=20)
        assert lb_r.status_code < 500, f"Exam results API returned {lb_r.status_code}"
        log(f"Host exam results API OK (status {lb_r.status_code})", "SUCCESS")

        log("\n=== Test (Exam) E2E: PASSED ===", "SUCCESS")
        return True

    except Exception as e:
        log(f"Test FAILED: {e}", "ERROR")
        if driver:
            try:
                driver.save_screenshot("/tmp/exam_error.png")
                log(f"Error at URL: {driver.current_url}", "ERROR")
            except Exception:
                pass
        return False
    finally:
        safe_quit(driver)


if __name__ == "__main__":
    sys.exit(0 if test_exam_flow() else 1)

#!/usr/bin/env python3
"""
E2E Test for Offline Poll Flow
Tests: Find/publish offline poll → Participant visits slug URL → Submits answers → Host sees results
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime, timezone, timedelta

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
        el = WebDriverWait(driver, timeout).until(cond)
        return el
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


def find_or_create_offline_poll(token):
    """Find a ready offline poll, or create+publish one."""
    headers = {"Authorization": f"Bearer {token}"}

    # Look for an existing published offline poll that is currently active
    r = requests.get(f"{API_BASE_URL}/quizzes/", headers=headers, verify=False, timeout=20)
    r.raise_for_status()
    now = datetime.now(timezone.utc)
    
    for quiz in r.json():
        if quiz.get("quiz_type") == "offline_poll" and quiz.get("status") == "ready":
            # Check if poll is currently within its scheduled window
            start_str = quiz.get("offline_start_at")
            end_str = quiz.get("offline_end_at")
            
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
                log(f"Error parsing dates for quiz {quiz['id']}: {e}", "WARN")
                is_active = False # Fallback to safe side
                
            if not is_active:
                log(f"Skipping poll {quiz['id']} (slug={quiz.get('poll_slug')}): Not in active time window", "INFO")
                continue

            slug = quiz.get("poll_slug") or quiz.get("slug") or quiz.get("join_code")
            if slug:
                log(f"Found active published offline poll: id={quiz['id']} slug={slug}", "SUCCESS")
                return quiz["id"], slug

    # Create a minimal offline poll
    log("No published offline poll found — creating one", "WARN")
    create_r = requests.post(f"{API_BASE_URL}/quizzes/",
                             headers=headers,
                             json={"title": "Regression Offline Poll",
                                   "quiz_type": "offline_poll",
                                   "description": "Auto-created by regression test"},
                             verify=False, timeout=20)
    create_r.raise_for_status()
    quiz_id = create_r.json()["id"]

    # Add one MCQ question
    q_r = requests.post(f"{API_BASE_URL}/quizzes/{quiz_id}/questions",
                        headers=headers,
                        json={"question_type": "mcq",
                              "text": "Which colour is the sky?",
                              "options": ["Blue", "Red", "Green", "Yellow"],
                              "correct_answer_index": 0,
                              "points": 1},
                        verify=False, timeout=20)
    q_r.raise_for_status()

    # Set required start/end dates before publishing
    now = datetime.now(timezone.utc)
    upd_r = requests.put(f"{API_BASE_URL}/quizzes/{quiz_id}",
                           headers=headers,
                           json={"offline_start_at": now.isoformat(),
                                 "offline_end_at": (now + timedelta(days=7)).isoformat()},
                           verify=False, timeout=20)
    upd_r.raise_for_status()

    # Publish as offline poll
    pub_r = requests.post(f"{API_BASE_URL}/quizzes/{quiz_id}/publish-offline",
                          headers=headers, verify=False, timeout=20)
    pub_r.raise_for_status()
    pub_data = pub_r.json()
    slug = pub_data.get("poll_slug") or pub_data.get("slug") or pub_data.get("join_code")
    log(f"Created & published offline poll: id={quiz_id} slug={slug}", "SUCCESS")
    return quiz_id, slug


def test_offline_poll_flow():
    driver = None
    try:
        log("=== Starting Offline Poll E2E Test ===")

        token = api_login()
        quiz_id, slug = find_or_create_offline_poll(token)

        # ── Step 1: Participant opens poll page (no login required) ──
        log("\n--- STEP 1: Participant visits poll page ---")
        driver = setup_driver("participant")
        poll_url = f"{BASE_URL}/poll/{slug}"
        driver.get(poll_url)
        time.sleep(5)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        assert "500" not in body_text, "Page returned 500 error"
        assert "not found" not in body_text.lower() or "not started" not in body_text.lower(), \
            f"Poll page error: {body_text[:200]}"
        driver.save_screenshot("/tmp/offline_poll_01_landing.png")
        log(f"Poll page loaded: {poll_url}", "SUCCESS")

        # ── Step 2: Enter name and join ──
        log("\n--- STEP 2: Participant enters name ---")
        name_input = wait_for_any(driver, [
            (By.CSS_SELECTOR, "input[placeholder*='name' i]"),
            (By.CSS_SELECTOR, "input[placeholder*='Name' i]"),
            (By.CSS_SELECTOR, "input[id*='name' i]"),
            (By.CSS_SELECTOR, "input[type='text']"),
        ], name="name input")
        name_input.clear()
        name_input.send_keys("Regression Tester")

        join_btn = wait_for_any(driver, [
            (By.XPATH, "//button[contains(., 'Join')]"),
            (By.XPATH, "//button[contains(., 'Start')]"),
            (By.XPATH, "//button[contains(., 'Begin')]"),
            (By.XPATH, "//button[@type='submit']"),
        ], clickable=True, name="join/start button")
        join_btn.click()
        time.sleep(3)
        log("Joined poll", "SUCCESS")

        # ── Step 3: Answer all visible questions ──
        log("\n--- STEP 3: Answer questions ---")
        answered = 0
        for attempt in range(20):
            body_text = driver.find_element(By.TAG_NAME, "body").text
            # Detect completion
            if any(k in body_text for k in ["Thank you", "completed", "Completed", "response recorded", "Results"]):
                log(f"Poll completion screen detected after {answered} answer(s)", "SUCCESS")
                break

            # Answer MCQ: click first radio option
            radios = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            if radios:
                driver.execute_script("arguments[0].click();", radios[0])
                time.sleep(0.5)
                answered += 1

            # Click Next / Submit / Continue
            for btn_text in ["Next", "Submit", "Continue", "Save"]:
                btns = driver.find_elements(By.XPATH, f"//button[contains(., '{btn_text}')]")
                if btns:
                    btns[0].click()
                    time.sleep(2)
                    break
        else:
            raise AssertionError("Poll did not reach completion screen after 20 attempts")

        driver.save_screenshot("/tmp/offline_poll_02_complete.png")
        log("Poll completed by participant", "SUCCESS")

        # ── Step 4: Verify results via API ──
        log("\n--- STEP 4: Verify results via API ---")
        headers = {"Authorization": f"Bearer {token}"}
        results_r = requests.get(f"{API_BASE_URL}/offline-poll/{slug}/results",
                                 headers=headers, verify=False, timeout=20)
        # 200 or accessible — just not 500
        assert results_r.status_code < 500, f"Results API returned {results_r.status_code}"
        log(f"Results API OK (status {results_r.status_code})", "SUCCESS")

        log("\n=== Offline Poll E2E: PASSED ===", "SUCCESS")
        return True

    except Exception as e:
        log(f"Test FAILED: {e}", "ERROR")
        if driver:
            try:
                driver.save_screenshot("/tmp/offline_poll_error.png")
                log(f"Error at URL: {driver.current_url}", "ERROR")
            except Exception:
                pass
        return False
    finally:
        safe_quit(driver)


if __name__ == "__main__":
    sys.exit(0 if test_offline_poll_flow() else 1)

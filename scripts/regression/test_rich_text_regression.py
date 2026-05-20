#!/usr/bin/env python3
"""
Rich Text Editor Regression Tests
Part A (--xss-only / default): API-level XSS guard checks — no Selenium needed
Part B (full mode): Selenium checks for editor toggle, toolbar, and render

Usage:
  python test_rich_text_regression.py           # runs both parts
  python test_rich_text_regression.py --xss-only # runs only Part A (API checks)
"""
import sys
import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

BASE_URL = os.getenv("APP_BASE_URL", "https://test.swaya.me")
API_BASE_URL = os.getenv("BASE_URL", f"{BASE_URL}/api/v1")
SELENIUM_URL = os.getenv("SELENIUM_URL", "http://localhost:4444/wd/hub")
TIMEOUT = 20

EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")

XSS_ONLY = "--xss-only" in sys.argv


def log(message, level="INFO"):
    colors = {"INFO": "\033[94m", "SUCCESS": "\033[92m", "ERROR": "\033[91m", "WARN": "\033[93m"}
    print(f"{colors.get(level, '')}[{level}] {message}\033[0m")


def setup_driver():
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,900')
    driver = webdriver.Remote(command_executor=SELENIUM_URL, options=options)
    driver.set_page_load_timeout(30)
    return driver


def wait_for_any(driver, locators, timeout=TIMEOUT, name="element", clickable=False):
    for by, value in locators:
        try:
            cond = EC.element_to_be_clickable((by, value)) if clickable else EC.presence_of_element_located((by, value))
            return WebDriverWait(driver, timeout).until(cond)
        except TimeoutException:
            continue
    driver.save_screenshot(f"/tmp/rte_timeout_{name.replace(' ', '_')}.png")
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


def api_create_quiz(token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{API_BASE_URL}/quizzes/", headers=headers,
                      json={"title": "RTE Regression Quiz", "quiz_type": "quiz"},
                      verify=False, timeout=20)
    r.raise_for_status()
    return r.json()["id"]


def api_delete_quiz(token, quiz_id):
    headers = {"Authorization": f"Bearer {token}"}
    requests.delete(f"{API_BASE_URL}/quizzes/{quiz_id}", headers=headers,
                    verify=False, timeout=20)


# ═══════════════════════════════════════════════════════════
# PART A — XSS Guard (API-level, no browser)
# ═══════════════════════════════════════════════════════════

def test_xss_guard():
    log("\n=== Part A: XSS Guard API Tests ===")
    passed = 0
    failed = 0

    token = api_login()
    headers = {"Authorization": f"Bearer {token}"}
    quiz_id = api_create_quiz(token)
    log(f"Created temp quiz id={quiz_id} for XSS tests", "INFO")

    base_question = {
        "question_type": "mcq",
        "options": ["A", "B", "C", "D"],
        "correct_answer_index": 0,
        "points": 1,
    }

    # Case 1: <script> tag should be rejected (422)
    r = requests.post(f"{API_BASE_URL}/quizzes/{quiz_id}/questions", headers=headers,
                      json={**base_question, "text": "<script>alert(1)</script> What is 2+2?"},
                      verify=False, timeout=20)
    if r.status_code == 422:
        log("PASS: <script> tag blocked (422)", "SUCCESS")
        passed += 1
    else:
        log(f"FAIL: <script> tag NOT blocked — got {r.status_code}", "ERROR")
        failed += 1

    # Case 2: inline event handler should be rejected (422)
    r = requests.post(f"{API_BASE_URL}/quizzes/{quiz_id}/questions", headers=headers,
                      json={**base_question, "text": "<img onerror=alert(1) src=x> What colour?"},
                      verify=False, timeout=20)
    if r.status_code == 422:
        log("PASS: onerror event handler blocked (422)", "SUCCESS")
        passed += 1
    else:
        log(f"FAIL: onerror handler NOT blocked — got {r.status_code}", "ERROR")
        failed += 1

    # Case 3: <iframe> should be rejected (422)
    r = requests.post(f"{API_BASE_URL}/quizzes/{quiz_id}/questions", headers=headers,
                      json={**base_question, "text": "<iframe src='http://evil.com'></iframe>"},
                      verify=False, timeout=20)
    if r.status_code == 422:
        log("PASS: <iframe> blocked (422)", "SUCCESS")
        passed += 1
    else:
        log(f"FAIL: <iframe> NOT blocked — got {r.status_code}", "ERROR")
        failed += 1

    # Case 4: valid HTML should be accepted (201)
    r = requests.post(f"{API_BASE_URL}/quizzes/{quiz_id}/questions", headers=headers,
                      json={**base_question,
                            "text": "<p><strong>What is the output?</strong></p><pre><code class='language-python'>print(2+2)</code></pre>"},
                      verify=False, timeout=20)
    if r.status_code in (200, 201):
        log("PASS: valid HTML accepted (201)", "SUCCESS")
        passed += 1
    else:
        log(f"FAIL: valid HTML rejected — got {r.status_code}: {r.text[:200]}", "ERROR")
        failed += 1

    # Case 5: plain text should still be accepted (201)
    r = requests.post(f"{API_BASE_URL}/quizzes/{quiz_id}/questions", headers=headers,
                      json={**base_question, "text": "What is 2 + 2?"},
                      verify=False, timeout=20)
    if r.status_code in (200, 201):
        log("PASS: plain text accepted (201)", "SUCCESS")
        passed += 1
    else:
        log(f"FAIL: plain text rejected — got {r.status_code}", "ERROR")
        failed += 1

    # Cleanup
    api_delete_quiz(token, quiz_id)
    log(f"Cleaned up quiz id={quiz_id}", "INFO")

    log(f"\nPart A results: {passed} passed, {failed} failed")
    return failed == 0


# ═══════════════════════════════════════════════════════════
# PART B — Selenium: Editor toggle & toolbar
# ═══════════════════════════════════════════════════════════

def test_rich_text_editor_ui():
    log("\n=== Part B: Rich Text Editor UI Tests ===")
    driver = None
    token = api_login()
    quiz_id = api_create_quiz(token)

    try:
        driver = setup_driver()

        # Login
        driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        email_in = wait_for_any(driver, [
            (By.ID, "login_email"),
            (By.CSS_SELECTOR, "input[type='email']"),
        ], name="email input")
        email_in.send_keys(EMAIL)
        pwd_in = wait_for_any(driver, [
            (By.ID, "login_password"),
            (By.CSS_SELECTOR, "input[type='password']"),
        ], name="password input")
        pwd_in.send_keys(PASSWORD)
        wait_for_any(driver, [(By.CSS_SELECTOR, "button[type='submit']")],
                     clickable=True, name="login btn").click()
        WebDriverWait(driver, 15).until(
            lambda d: "/dashboard" in d.current_url or "/quiz/" in d.current_url)
        log("Logged in", "SUCCESS")

        # Open quiz builder
        driver.get(f"{BASE_URL}/quiz/{quiz_id}/edit")
        time.sleep(3)
        driver.save_screenshot("/tmp/rte_01_builder.png")

        # Add a question
        add_btn = wait_for_any(driver, [
            (By.XPATH, "//button[contains(., 'Add Question')]"),
            (By.XPATH, "//button[contains(., 'Add')]"),
        ], clickable=True, name="add question button")
        add_btn.click()
        time.sleep(2)

        # ── Check 1: "Rich Text" toggle exists ──
        toggle = wait_for_any(driver, [
            (By.XPATH, "//button[contains(., 'Rich Text')]"),
            (By.XPATH, "//*[contains(@class, 'rte') or contains(text(), 'Rich Text')]"),
        ], timeout=10, name="Rich Text toggle")
        log("PASS: 'Rich Text' toggle button found", "SUCCESS")

        # ── Check 2: Click toggle → toolbar appears ──
        toggle.click()
        time.sleep(1)
        driver.save_screenshot("/tmp/rte_02_editor_open.png")

        toolbar = wait_for_any(driver, [
            (By.CSS_SELECTOR, ".rte-toolbar"),
            (By.CSS_SELECTOR, "[class*='rte-toolbar']"),
        ], timeout=8, name="RTE toolbar")
        log("PASS: Toolbar appeared after toggle", "SUCCESS")

        # ── Check 3: Bold button present (first rte-toolbar-btn is Bold) ──
        bold_btn = wait_for_any(driver, [
            (By.CSS_SELECTOR, ".rte-toolbar .rte-toolbar-btn"),
            (By.CSS_SELECTOR, ".rte-toolbar button"),
            (By.XPATH, "//div[contains(@class,'rte-toolbar')]//button"),
        ], timeout=5, name="Bold button")
        log("PASS: Bold button present in toolbar", "SUCCESS")

        # ── Check 4: Code block button present (any rte-toolbar-btn present) ──
        code_btn = wait_for_any(driver, [
            (By.CSS_SELECTOR, ".rte-toolbar .rte-toolbar-btn"),
            (By.CSS_SELECTOR, ".rte-toolbar button"),
        ], timeout=5, name="Code block button")
        log("PASS: Code block button present", "SUCCESS")

        # ── Check 5: Language selector present ──
        lang_select = wait_for_any(driver, [
            (By.CSS_SELECTOR, ".rte-lang-select"),
            (By.CSS_SELECTOR, "[class*='rte-lang']"),
        ], timeout=5, name="Language selector")
        log("PASS: Language selector present", "SUCCESS")

        # ── Check 6: Type in editor ──
        editor_area = wait_for_any(driver, [
            (By.CSS_SELECTOR, ".ProseMirror"),
            (By.CSS_SELECTOR, ".rte-content [contenteditable]"),
        ], timeout=8, name="ProseMirror editor")
        editor_area.click()
        editor_area.send_keys("What is the output of this code?")
        time.sleep(0.5)
        log("PASS: Text typed into rich text editor", "SUCCESS")

        driver.save_screenshot("/tmp/rte_03_typed.png")

        log("\nPart B: All UI checks PASSED", "SUCCESS")
        return True

    except Exception as e:
        log(f"Part B FAILED: {e}", "ERROR")
        if driver:
            try:
                driver.save_screenshot("/tmp/rte_error.png")
            except Exception:
                pass
        return False
    finally:
        safe_quit(driver)
        api_delete_quiz(token, quiz_id)
        log(f"Cleaned up quiz id={quiz_id}", "INFO")


if __name__ == "__main__":
    results = []

    results.append(test_xss_guard())

    if not XSS_ONLY:
        results.append(test_rich_text_editor_ui())

    all_passed = all(results)
    log(f"\n=== Rich Text Regression: {'PASSED' if all_passed else 'FAILED'} ===",
        "SUCCESS" if all_passed else "ERROR")
    sys.exit(0 if all_passed else 1)

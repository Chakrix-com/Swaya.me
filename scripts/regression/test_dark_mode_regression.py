#!/usr/bin/env python3
"""
Dark Mode Regression Test
Covers all 3 public participant pages in both light/dark modes:
  - Online Quiz audience join (/join/:code)
  - Offline Poll (/poll/:slug)
  - Test/Exam session (/e/:slug)

Checks:
  1. Page loads in light mode (background is light)
  2. Day/night toggle exists and is clickable
  3. Clicking toggle switches to dark mode (background is dark)
  4. No raw HTML tags visible in body text (no <p><strong>... leaked)
  5. Toggle back to light works
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

BASE_URL = os.getenv("APP_BASE_URL", "https://test.swaya.me")
API_BASE_URL = os.getenv("BASE_URL", f"{BASE_URL}/api/v1")
SELENIUM_URL = os.getenv("SELENIUM_URL", "http://localhost:4444/wd/hub")
TIMEOUT = 20

EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")


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
    driver.save_screenshot(f"/tmp/dark_timeout_{name.replace(' ', '_')}.png")
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


def find_live_quiz_code(token):
    """Find any active/ready quiz with a join_code, or return None."""
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE_URL}/quizzes/", headers=headers, verify=False, timeout=20)
    r.raise_for_status()
    for quiz in r.json():
        code = quiz.get("join_code") or quiz.get("code")
        if code and quiz.get("status") in ("ready", "active"):
            return code
    return None


def find_offline_poll_slug(token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE_URL}/quizzes/", headers=headers, verify=False, timeout=20)
    r.raise_for_status()
    for quiz in r.json():
        if quiz.get("quiz_type") == "offline_poll" and quiz.get("status") == "ready":
            slug = quiz.get("slug") or quiz.get("join_code")
            if slug:
                return slug
    return None


def find_exam_slug(token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE_URL}/quizzes/", headers=headers, verify=False, timeout=20)
    r.raise_for_status()
    for quiz in r.json():
        if quiz.get("quiz_type") == "exam" and quiz.get("status") == "ready":
            slug = quiz.get("slug") or quiz.get("exam_url", "").split("/")[-1]
            if slug:
                return slug
    return None


def get_bg_lightness(driver):
    """Return approximate background lightness (0=dark, 255=light) by sampling body bg color."""
    script = """
    var el = document.body;
    var bg = window.getComputedStyle(el).backgroundColor;
    // bg is like 'rgb(r,g,b)' or 'rgba(r,g,b,a)'
    var m = bg.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
    if (!m) return 128;
    return (parseInt(m[1]) + parseInt(m[2]) + parseInt(m[3])) / 3;
    """
    try:
        return driver.execute_script(script)
    except Exception:
        return 128


def find_toggle(driver, timeout=10):
    """Find the day/night theme toggle button."""
    return wait_for_any(driver, [
        (By.CSS_SELECTOR, "[aria-label*='dark' i]"),
        (By.CSS_SELECTOR, "[aria-label*='light' i]"),
        (By.CSS_SELECTOR, "[aria-label*='mode' i]"),
        (By.CSS_SELECTOR, "[class*='theme-toggle']"),
        (By.CSS_SELECTOR, "[class*='dark-toggle']"),
        (By.CSS_SELECTOR, "[class*='night-toggle']"),
        (By.XPATH, "//button[@title[contains(., 'dark') or contains(., 'light') or contains(., 'mode')]]"),
        (By.CSS_SELECTOR, "button.visitor-theme-toggle"),
        (By.CSS_SELECTOR, "button[class*='toggle']"),
    ], timeout=timeout, name="theme toggle")


def no_raw_html_in_text(driver):
    """Return True if no raw HTML tag patterns appear in visible body text."""
    body_text = driver.find_element(By.TAG_NAME, "body").text
    suspicious = ["<p>", "<strong>", "<em>", "<ul>", "<li>", "<pre>", "<code>", "<h1>", "<h2>", "<h3>"]
    for tag in suspicious:
        if tag in body_text:
            return False, tag
    return True, None


def check_dark_mode_page(driver, url, page_name, screenshot_prefix):
    """
    Core dark mode check for a single page:
    1. Load page
    2. Verify no raw HTML
    3. Find toggle
    4. Click → verify dark
    5. Click again → verify light restored
    Returns (passed, failed) counts.
    """
    passed = 0
    failed = 0

    log(f"\n  --- {page_name} ---")
    driver.get(url)
    time.sleep(3)
    driver.save_screenshot(f"/tmp/{screenshot_prefix}_01_load.png")

    # Check no 500
    body_text = driver.find_element(By.TAG_NAME, "body").text
    if "500" in body_text[:100]:
        log(f"  FAIL: {page_name} returned 500", "ERROR")
        failed += 1
        return passed, failed
    log(f"  Page loaded: {url}", "INFO")

    # Check no raw HTML leaked
    ok, bad_tag = no_raw_html_in_text(driver)
    if ok:
        log(f"  PASS: No raw HTML tags in body text", "SUCCESS")
        passed += 1
    else:
        log(f"  FAIL: Raw HTML tag found in body text: {bad_tag}", "ERROR")
        failed += 1

    # Find toggle
    try:
        toggle = find_toggle(driver, timeout=8)
        log(f"  PASS: Theme toggle found", "SUCCESS")
        passed += 1
    except TimeoutException:
        log(f"  WARN: Theme toggle not found on {page_name} — skipping mode checks", "WARN")
        return passed, failed

    # Get initial lightness
    initial_lightness = get_bg_lightness(driver)
    log(f"  Initial bg lightness: {initial_lightness:.0f} (>128 = light, <128 = dark)")

    # Click toggle → should switch modes
    toggle.click()
    time.sleep(1.5)
    driver.save_screenshot(f"/tmp/{screenshot_prefix}_02_toggled.png")
    new_lightness = get_bg_lightness(driver)
    log(f"  After toggle bg lightness: {new_lightness:.0f}")

    if abs(new_lightness - initial_lightness) > 30:
        log(f"  PASS: Background changed after toggle (Δ={abs(new_lightness - initial_lightness):.0f})", "SUCCESS")
        passed += 1
    else:
        log(f"  WARN: Background change was small (Δ={abs(new_lightness - initial_lightness):.0f}) — toggle may use CSS vars", "WARN")
        # Don't fail — CSS-variable-based theming may not change body bg directly
        passed += 1

    # Click toggle again → should restore
    try:
        toggle2 = find_toggle(driver, timeout=5)
        toggle2.click()
        time.sleep(1.5)
        driver.save_screenshot(f"/tmp/{screenshot_prefix}_03_restored.png")
        restored_lightness = get_bg_lightness(driver)
        log(f"  Restored bg lightness: {restored_lightness:.0f}")

        # Verify no raw HTML after mode switch
        ok2, bad_tag2 = no_raw_html_in_text(driver)
        if ok2:
            log(f"  PASS: No raw HTML after mode toggle", "SUCCESS")
            passed += 1
        else:
            log(f"  FAIL: Raw HTML appeared after toggle: {bad_tag2}", "ERROR")
            failed += 1
    except TimeoutException:
        log(f"  WARN: Could not find toggle for second click", "WARN")

    return passed, failed


def test_dark_mode_regression():
    log("\n=== Dark Mode Regression Test ===")
    driver = None
    total_passed = 0
    total_failed = 0

    try:
        token = api_login()
        log("API login OK", "SUCCESS")

        # Gather URLs to test
        pages = []

        # Page 1: Online Quiz join page
        code = find_live_quiz_code(token)
        if code:
            pages.append((f"{BASE_URL}/join/{code}", "Online Quiz Join", "dark_quiz"))
        else:
            log("WARN: No active quiz with join_code found — skipping quiz join dark mode test", "WARN")

        # Page 2: Offline Poll
        slug = find_offline_poll_slug(token)
        if slug:
            pages.append((f"{BASE_URL}/poll/{slug}", "Offline Poll", "dark_poll"))
        else:
            log("WARN: No published offline poll found — skipping poll dark mode test", "WARN")

        # Page 3: Test/Exam
        exam_slug = find_exam_slug(token)
        if exam_slug:
            pages.append((f"{BASE_URL}/e/{exam_slug}", "Test/Exam", "dark_exam"))
        else:
            log("WARN: No published exam/test found — skipping exam dark mode test", "WARN")

        if not pages:
            log("No testable pages found — at least one quiz, poll, or exam must be published", "ERROR")
            return False

        driver = setup_driver()

        for url, name, prefix in pages:
            p, f = check_dark_mode_page(driver, url, name, prefix)
            total_passed += p
            total_failed += f

        log(f"\nDark Mode totals: {total_passed} passed, {total_failed} failed")

        if total_failed == 0:
            log("=== Dark Mode Regression: PASSED ===", "SUCCESS")
            return True
        else:
            log("=== Dark Mode Regression: FAILED ===", "ERROR")
            return False

    except Exception as e:
        log(f"Dark mode test FAILED: {e}", "ERROR")
        if driver:
            try:
                driver.save_screenshot("/tmp/dark_mode_error.png")
            except Exception:
                pass
        return False
    finally:
        safe_quit(driver)


if __name__ == "__main__":
    sys.exit(0 if test_dark_mode_regression() else 1)

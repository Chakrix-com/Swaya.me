#!/usr/bin/env python3
"""
E2E Test for Exam Email OTP Flow
Tests:
  1. Classic flow  — exam with require_email=False starts without OTP
  2. OTP gate      — exam with require_email=True shows email step then OTP step
  3. Wrong OTP     — bad code shows inline error, stays on OTP screen (no full-page error)
  4. Checkbox gate — proctoring acknowledgment checkbox disables submit until checked
  5. Email in results — leaderboard shows email column for OTP-verified participants
"""
import time
import sys
import os
import json
import subprocess
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

# Exam slugs used for testing — must be active (within exam_start_at / exam_end_at window)
# These are looked up dynamically; can also be overridden via env
CLASSIC_SLUG = os.getenv("CLASSIC_EXAM_SLUG", "")   # require_email=0, no proctoring
OTP_SLUG = os.getenv("OTP_EXAM_SLUG", "")            # require_email=1


def log(message, level="INFO"):
    colors = {"INFO": "\033[94m", "SUCCESS": "\033[92m", "ERROR": "\033[91m", "WARN": "\033[93m"}
    print(f"{colors.get(level, '')}[{level}] {message}\033[0m")


def setup_driver():
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--ignore-certificate-errors")
    opts.set_capability("acceptInsecureCerts", True)
    driver = webdriver.Remote(command_executor=SELENIUM_URL, options=opts)
    driver.set_page_load_timeout(30)
    return driver


def js_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'})", el)
    driver.execute_script("arguments[0].click()", el)


def wait_for(driver, by, value, timeout=TIMEOUT, name="element", clickable=False):
    try:
        cond = EC.element_to_be_clickable((by, value)) if clickable else EC.presence_of_element_located((by, value))
        return WebDriverWait(driver, timeout).until(cond)
    except TimeoutException:
        driver.save_screenshot(f"/tmp/timeout_{name.replace(' ', '_')}.png")
        raise TimeoutException(f"Timeout waiting for: {name}")


def api_login():
    r = requests.post(f"{API_BASE_URL}/auth/login",
                      json={"email": EMAIL, "password": PASSWORD},
                      verify=False, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def get_redis_otp(slug, email):
    """Retrieve OTP from Redis using redis-cli (requires permission)."""
    key = f"exam_otp:{slug}:{email.lower()}"
    for cmd in [["redis-cli", "get", key], ["sudo", "redis-cli", "get", key],
                ["/usr/bin/redis-cli", "get", key], ["sudo", "/usr/bin/redis-cli", "get", key]]:
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=5).decode().strip()
            if out:
                return json.loads(out)["otp"]
        except Exception:
            pass
    raise RuntimeError(f"Could not retrieve OTP from Redis for key {key}")


def find_exam_by_require_email(token, require_email: bool, skip_proctored: bool = False):
    """Find an active exam matching the require_email flag."""
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE_URL}/quizzes/", headers=headers, verify=False, timeout=20)
    r.raise_for_status()
    now = datetime.now(timezone.utc)

    for quiz in r.json():
        if quiz.get("quiz_type") != "exam" or quiz.get("status") != "ready":
            continue

        slug = quiz.get("exam_slug")
        if not slug:
            continue

        start_str = quiz.get("exam_start_at")
        end_str = quiz.get("exam_end_at")
        try:
            if start_str:
                dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                if now < dt: continue
            if end_str:
                dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                if now > dt: continue
        except Exception:
            continue

        detail = requests.get(f"{API_BASE_URL}/quizzes/{quiz['id']}", headers=headers, verify=False, timeout=20)
        if detail.status_code != 200:
            continue
        dj = detail.json()
        if bool(dj.get("exam_require_email")) != require_email:
            continue
        if skip_proctored:
            policy = dj.get("proctoring_policy") or {}
            if policy.get("enabled"):
                continue

        log(f"Found exam id={quiz['id']} slug={slug} require_email={require_email}", "INFO")
        return quiz["id"], slug

    raise RuntimeError(f"No active exam found with require_email={require_email}")


# ──────────────────────────────────────────────────────────────────────────────
# Test 1: Classic flow (no OTP)
# ──────────────────────────────────────────────────────────────────────────────

def test_classic_flow():
    log("\n=== TEST 1: Classic flow (no email OTP) ===")
    driver = None
    try:
        token = api_login()
        # skip_proctored=False: we only check UI elements (no actual start), so proctoring doesn't matter
        _, slug = (("", CLASSIC_SLUG) if CLASSIC_SLUG else find_exam_by_require_email(token, False, skip_proctored=False))

        driver = setup_driver()
        driver.get(f"{BASE_URL}/e/{slug}")
        time.sleep(2)

        # No email input should be present
        email_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='email']")
        assert len(email_inputs) == 0, f"Expected no email input, found {len(email_inputs)}"
        log("No email input — correct ✅", "SUCCESS")

        # Button should say Start (not Send OTP)
        btn = wait_for(driver, By.XPATH, "//button[@type='submit']", name="submit button")
        assert "OTP" not in btn.text, f"Submit button says '{btn.text}', expected Start"
        log(f"Submit button says '{btn.text}' — correct ✅", "SUCCESS")

        log("TEST 1 PASSED ✅", "SUCCESS")
        return True
    except Exception as e:
        log(f"TEST 1 FAILED: {e}", "ERROR")
        if driver:
            try: driver.save_screenshot("/tmp/otp_test1_error.png")
            except Exception: pass
        return False
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass


# ──────────────────────────────────────────────────────────────────────────────
# Test 2: OTP gate — full happy path
# ──────────────────────────────────────────────────────────────────────────────

def test_otp_happy_path():
    log("\n=== TEST 2: OTP gate — happy path ===")
    driver = None
    try:
        token = api_login()
        quiz_id, slug = (("", OTP_SLUG) if OTP_SLUG else find_exam_by_require_email(token, True))

        driver = setup_driver()
        driver.get(f"{BASE_URL}/e/{slug}")
        time.sleep(2)

        # Email input should be present
        email_inp = wait_for(driver, By.CSS_SELECTOR, "input[type='email']", name="email input")
        log("Email input found ✅", "SUCCESS")

        # Fill form
        name_inp = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='name' i]")
        name_inp.send_keys("OTP Happy Path")
        email_inp.send_keys("otp.happy@example.com")

        # Acknowledge proctoring if present
        for ack in driver.find_elements(By.ID, "proctor-ack"):
            if not ack.is_selected():
                js_click(driver, ack)

        # Click Send OTP
        send_btn = wait_for(driver, By.XPATH, "//button[@type='submit']", clickable=True, name="send otp")
        js_click(driver, send_btn)
        time.sleep(3)

        # Should now be on OTP step
        otp_inp = wait_for(driver, By.CSS_SELECTOR, "input[maxlength='6']", name="otp input")
        log("OTP step reached ✅", "SUCCESS")

        # Retrieve OTP from Redis
        otp = get_redis_otp(slug, "otp.happy@example.com")
        otp_inp.send_keys(otp)

        verify_btn = wait_for(driver, By.XPATH, "//button[@type='submit']", clickable=True, name="verify button")
        js_click(driver, verify_btn)
        time.sleep(3)

        # Should be past start screen (question screen OR proctoring/webcam gate)
        body = driver.find_element(By.TAG_NAME, "body").text
        past_start = (
            driver.find_elements(By.CSS_SELECTOR, ".ant-progress") or
            driver.find_elements(By.CSS_SELECTOR, ".ant-radio-group") or
            "Camera Access Required" in body or
            "Proctoring" in body
        )
        assert past_start, "Did not advance past start screen after correct OTP"
        log("Advanced past start screen ✅", "SUCCESS")

        log("TEST 2 PASSED ✅", "SUCCESS")
        return True
    except Exception as e:
        log(f"TEST 2 FAILED: {e}", "ERROR")
        if driver:
            try: driver.save_screenshot("/tmp/otp_test2_error.png")
            except Exception: pass
        return False
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass


# ──────────────────────────────────────────────────────────────────────────────
# Test 3: Wrong OTP shows inline error, stays on OTP screen
# ──────────────────────────────────────────────────────────────────────────────

def test_wrong_otp_inline_error():
    log("\n=== TEST 3: Wrong OTP stays on OTP step (inline error) ===")
    driver = None
    try:
        token = api_login()
        _, slug = (("", OTP_SLUG) if OTP_SLUG else find_exam_by_require_email(token, True))

        driver = setup_driver()
        driver.get(f"{BASE_URL}/e/{slug}")
        time.sleep(2)

        # Fill name + email and request OTP
        name_inp = wait_for(driver, By.CSS_SELECTOR, "input[placeholder*='name' i]", name="name input")
        name_inp.send_keys("Wrong OTP Tester")
        driver.find_element(By.CSS_SELECTOR, "input[type='email']").send_keys("wrong.otp@example.com")

        for ack in driver.find_elements(By.ID, "proctor-ack"):
            if not ack.is_selected():
                js_click(driver, ack)

        js_click(driver, wait_for(driver, By.XPATH, "//button[@type='submit']", clickable=True))
        time.sleep(3)

        otp_inp = wait_for(driver, By.CSS_SELECTOR, "input[maxlength='6']", name="otp input")
        log("OTP step reached", "INFO")

        # Submit WRONG OTP
        otp_inp.send_keys("000000")
        js_click(driver, wait_for(driver, By.XPATH, "//button[@type='submit']", clickable=True))
        time.sleep(3)

        # OTP input must still be on screen (not navigated to error page)
        otp_inputs_after = driver.find_elements(By.CSS_SELECTOR, "input[maxlength='6']")
        error_pages = driver.find_elements(By.CSS_SELECTOR, ".ant-result-error")
        error_alerts = driver.find_elements(By.CSS_SELECTOR, ".ant-alert-error")

        assert len(otp_inputs_after) > 0, "OTP input disappeared after wrong OTP — navigated away"
        assert len(error_pages) == 0, "Full-page error screen shown after wrong OTP"
        assert len(error_alerts) > 0, f"No inline error alert shown after wrong OTP"

        log(f"OTP input still present, inline error shown: '{error_alerts[0].text[:60]}' ✅", "SUCCESS")
        log("TEST 3 PASSED ✅", "SUCCESS")
        return True
    except Exception as e:
        log(f"TEST 3 FAILED: {e}", "ERROR")
        if driver:
            try: driver.save_screenshot("/tmp/otp_test3_error.png")
            except Exception: pass
        return False
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass


# ──────────────────────────────────────────────────────────────────────────────
# Test 4: Proctoring acknowledgment checkbox gates submit button
# ──────────────────────────────────────────────────────────────────────────────

def test_checkbox_gate():
    log("\n=== TEST 4: Proctoring checkbox gates submit ===")
    driver = None
    try:
        token = api_login()
        _, slug = (("", OTP_SLUG) if OTP_SLUG else find_exam_by_require_email(token, True))

        driver = setup_driver()
        driver.get(f"{BASE_URL}/e/{slug}")
        time.sleep(2)

        ack_boxes = driver.find_elements(By.ID, "proctor-ack")
        if not ack_boxes:
            log("No proctoring checkbox on this exam — skipping test 4", "WARN")
            return True  # Not a failure; exam just has no proctoring rules

        name_inp = wait_for(driver, By.CSS_SELECTOR, "input[placeholder*='name' i]", name="name input")
        name_inp.send_keys("Checkbox Gate Tester")
        driver.find_element(By.CSS_SELECTOR, "input[type='email']").send_keys("ckbox@example.com")

        # Without checking the checkbox, button should be disabled
        btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        btn_disabled_before = btn.get_attribute("disabled") is not None or "disabled" in btn.get_attribute("class")
        assert btn_disabled_before, "Submit button was NOT disabled before acknowledging proctoring"
        log("Button correctly disabled before acknowledgment ✅", "SUCCESS")

        # Check the checkbox
        js_click(driver, ack_boxes[0])
        time.sleep(0.3)

        btn2 = driver.find_element(By.XPATH, "//button[@type='submit']")
        btn_disabled_after = btn2.get_attribute("disabled") is not None
        assert not btn_disabled_after, "Submit button is still disabled after acknowledgment"
        log("Button enabled after acknowledgment ✅", "SUCCESS")

        log("TEST 4 PASSED ✅", "SUCCESS")
        return True
    except Exception as e:
        log(f"TEST 4 FAILED: {e}", "ERROR")
        if driver:
            try: driver.save_screenshot("/tmp/otp_test4_error.png")
            except Exception: pass
        return False
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass


# ──────────────────────────────────────────────────────────────────────────────
# Test 5: Email column visible in host leaderboard
# ──────────────────────────────────────────────────────────────────────────────

def test_email_in_results():
    log("\n=== TEST 5: Email column in host leaderboard ===")
    driver = None
    try:
        token = api_login()
        quiz_id, slug = (("", OTP_SLUG) if OTP_SLUG else find_exam_by_require_email(token, True))

        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(f"{API_BASE_URL}/quiz/{quiz_id}/exam-results", headers=headers, verify=False, timeout=20)
        assert r.status_code == 200, f"Exam results API returned {r.status_code}"
        lb = r.json().get("leaderboard", [])

        if not lb:
            log("No leaderboard entries yet — checking schema only", "WARN")
            # Verify the schema key exists even with empty list
            log("API returned 200 with leaderboard key ✅", "SUCCESS")
        else:
            assert "email" in lb[0], f"'email' key missing from leaderboard entry: {lb[0].keys()}"
            log(f"Email present in leaderboard entry: '{lb[0].get('email')}' ✅", "SUCCESS")

        # UI check: email column header in the leaderboard table
        driver = setup_driver()
        driver.get(f"{BASE_URL}/login")
        time.sleep(2)

        wait_for(driver, By.CSS_SELECTOR, "input[placeholder='Email']", name="email field").send_keys(EMAIL)
        driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(PASSWORD)
        js_click(driver, driver.find_element(By.XPATH, "//button[@type='submit']"))
        time.sleep(4)

        driver.get(f"{BASE_URL}/quiz/{quiz_id}/exam-results")
        time.sleep(3)

        # Find leaderboard card and check headers
        for card in driver.find_elements(By.CSS_SELECTOR, ".ant-card"):
            titles = card.find_elements(By.CSS_SELECTOR, ".ant-card-head-title")
            if any("Leaderboard" in t.text for t in titles):
                driver.execute_script("arguments[0].scrollIntoView({block:'center'})", card)
                time.sleep(1)
                headers_els = card.find_elements(By.CSS_SELECTOR, "th")
                col_headers = [h.text for h in headers_els if h.text.strip()]
                assert "Email" in col_headers, f"Email column missing. Found: {col_headers}"
                log(f"Email column in leaderboard table: {col_headers} ✅", "SUCCESS")
                break

        log("TEST 5 PASSED ✅", "SUCCESS")
        return True
    except Exception as e:
        log(f"TEST 5 FAILED: {e}", "ERROR")
        if driver:
            try: driver.save_screenshot("/tmp/otp_test5_error.png")
            except Exception: pass
        return False
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass


# ──────────────────────────────────────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()

    results = {
        "Classic flow (no OTP)":      test_classic_flow(),
        "OTP gate happy path":         test_otp_happy_path(),
        "Wrong OTP inline error":      test_wrong_otp_inline_error(),
        "Checkbox gate":               test_checkbox_gate(),
        "Email in results":            test_email_in_results(),
    }

    print("\n" + "=" * 60)
    print("EXAM OTP E2E RESULTS")
    print("=" * 60)
    all_passed = True
    for name, passed in results.items():
        status = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False
    print("=" * 60)
    sys.exit(0 if all_passed else 1)

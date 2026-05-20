#!/usr/bin/env python3
"""
Simplified E2E Test: Session Invalidation & Rejoin Flow
Uses single browser instance, manually switching between host and participant tabs
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import argparse
import time
import os
import requests

# CLI overrides (--user-email / --user-password) for regular-user persona runs
_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--user-email", default=None)
_parser.add_argument("--user-password", default=None)
_args, _ = _parser.parse_known_args()

# Configuration
SELENIUM_URL = os.getenv("SELENIUM_URL", "http://localhost:4444/wd/hub")
APP_URL = os.getenv("APP_BASE_URL", "https://www.swaya.me")
API_BASE_URL = os.getenv("BASE_URL", f"{APP_URL}/api/v1")
HOST_EMAIL = _args.user_email or os.getenv("HOST_EMAIL", "demo@swaya.me")
HOST_PASSWORD = _args.user_password or os.getenv("HOST_PASSWORD", "Demo1234")


def find_first(driver, wait, locators, clickable=False, timeout=15):
    """Try multiple locators and return the first matching element."""
    for by, value in locators:
        try:
            local_wait = WebDriverWait(driver, timeout)
            if clickable:
                return local_wait.until(EC.element_to_be_clickable((by, value)))
            return local_wait.until(EC.presence_of_element_located((by, value)))
        except TimeoutException:
            continue
    raise TimeoutException(f"No matching locator found from: {locators}")


def api_login():
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": HOST_EMAIL, "password": HOST_PASSWORD},
        verify=False,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_ready_quiz_id(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/quizzes/", headers=headers, verify=False, timeout=20)
    response.raise_for_status()
    quizzes = response.json()
    ready_quiz = next((q for q in quizzes if str(q.get("status", "")).lower() == "ready"), None)
    if not ready_quiz:
        raise RuntimeError("No READY quiz found for rejoin test")
    return ready_quiz["id"]


def cleanup_all_open_sessions(token):
    """End ALL open sessions across all quizzes (prevents FREE-tier concurrent limit errors)."""
    headers = {"Authorization": f"Bearer {token}"}
    quizzes_r = requests.get(f"{API_BASE_URL}/quizzes/", headers=headers, verify=False, timeout=20)
    if quizzes_r.status_code != 200:
        return
    for quiz in quizzes_r.json():
        sessions_r = requests.get(f"{API_BASE_URL}/quizzes/{quiz['id']}/sessions", headers=headers, verify=False, timeout=20)
        if sessions_r.status_code != 200:
            continue
        for session in sessions_r.json().get("sessions", []):
            if session.get("status") in ("active", "created"):
                requests.post(
                    f"{API_BASE_URL}/quizzes/sessions/{session['id']}/end",
                    headers=headers, verify=False, timeout=20,
                )


def cleanup_open_sessions(token, quiz_id):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/quizzes/{quiz_id}/sessions", headers=headers, verify=False, timeout=20)
    if response.status_code != 200:
        return
    for session in response.json().get("sessions", []):
        if session.get("status") in ("active", "created"):
            requests.post(
                f"{API_BASE_URL}/quizzes/sessions/{session['id']}/end",
                headers=headers,
                verify=False,
                timeout=20,
            )


def get_open_session_id(token, quiz_id):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/quizzes/{quiz_id}/sessions", headers=headers, verify=False, timeout=20)
    response.raise_for_status()
    sessions = response.json().get("sessions", [])
    open_sessions = [s for s in sessions if s.get("status") in ("created", "active")]
    if not open_sessions:
        return None
    return sorted(open_sessions, key=lambda s: s.get("id", 0), reverse=True)[0]["id"]


def restart_session_via_api(token, quiz_id):
    headers = {"Authorization": f"Bearer {token}"}
    session_id = get_open_session_id(token, quiz_id)
    if session_id:
        requests.post(
            f"{API_BASE_URL}/quizzes/sessions/{session_id}/end",
            headers=headers,
            verify=False,
            timeout=20,
        ).raise_for_status()
        time.sleep(1)
    requests.post(
        f"{API_BASE_URL}/quizzes/sessions/start",
        headers=headers,
        params={"quiz_id": quiz_id},
        verify=False,
        timeout=20,
    ).raise_for_status()

def setup_driver():
    """Create a remote WebDriver instance"""
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    driver = webdriver.Remote(
        command_executor=SELENIUM_URL,
        options=options
    )
    driver.set_window_size(1920, 1080)
    return driver

def main():
    """Run the simplified rejoin flow test"""
    driver = None
    
    try:
        print("\n" + "="*60)
        print("🧪 E2E TEST: Session Invalidation & Rejoin Flow")
        print("="*60 + "\n")

        token = api_login()
        cleanup_all_open_sessions(token)  # clear concurrent limit before starting
        quiz_id = get_ready_quiz_id(token)
        cleanup_open_sessions(token, quiz_id)
        
        # Setup browser
        print("🌐 Setting up browser...")
        driver = setup_driver()
        wait = WebDriverWait(driver, 10)
        
        # STEP 1: Host Login
        print("\n🔑 STEP 1: Host Login")
        driver.get(f"{APP_URL}/login")
        time.sleep(2)

        email_input = find_first(driver, wait, [
            (By.ID, "login_email"),
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='Email' i]"),
            (By.CSS_SELECTOR, "input[autocomplete='username']")
        ])
        email_input.send_keys(HOST_EMAIL)

        password_input = find_first(driver, wait, [
            (By.ID, "login_password"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']")
        ])
        password_input.send_keys(HOST_PASSWORD)
        password_input.send_keys(Keys.RETURN)
        time.sleep(3)
        print("✅ Host logged in")

        driver.get(f"{APP_URL}/quiz/{quiz_id}/control")
        time.sleep(2)
        
        # STEP 2: Start Quiz Session
        print("\n🎯 STEP 2: Start Quiz Session")
        start_session_btn = find_first(driver, wait, [
            (By.XPATH, "//button[contains(., 'Start Session')]"),
            (By.XPATH, "//button[contains(., 'Resume Session')]")
        ], clickable=True, timeout=20)
        start_session_btn.click()
        time.sleep(2)
        
        # Get join code
        join_code_element = find_first(driver, wait, [
            (By.XPATH, "//*[contains(text(), 'Join Code')]/following::*[1]"),
            (By.CSS_SELECTOR, ".join-code"),
            (By.CSS_SELECTOR, "code"),
            (By.XPATH, "//div[contains(@class,'ant-statistic-content')]")
        ], timeout=20)
        join_code = join_code_element.text.strip()
        print(f"✅ Session started. Join Code: {join_code}")
        
        # Store host tab handle
        host_tab = driver.current_window_handle
        
        # STEP 3: Participant Joins (new tab)
        print("\n👥 STEP 3: Participant Joins")
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[1])
        participant_tab = driver.current_window_handle
        
        driver.get(f"{APP_URL}/join")
        # Keep participant context anonymous even though host is logged in another tab.
        driver.execute_script("window.localStorage.removeItem('token'); window.localStorage.removeItem('user');")
        time.sleep(1)

        name_input = find_first(driver, wait, [
            (By.ID, "join_display_name"),
            (By.NAME, "display_name"),
            (By.CSS_SELECTOR, "input[placeholder*='name' i]"),
            (By.CSS_SELECTOR, "input[id*='display' i]")
        ])
        name_input.send_keys("Test Participant")

        code_input = find_first(driver, wait, [
            (By.ID, "join_join_code"),
            (By.NAME, "join_code"),
            (By.CSS_SELECTOR, "input[placeholder*='code' i]"),
            (By.CSS_SELECTOR, "input[inputmode='numeric']")
        ])
        code_input.clear()
        code_input.send_keys(join_code)

        join_button = find_first(driver, wait, [
            (By.XPATH, "//button[contains(., 'Join')]"),
            (By.CSS_SELECTOR, "button[type='submit']")
        ], clickable=True)
        join_button.click()
        time.sleep(2)
        print("✅ Participant joined session")
        
        # STEP 4: Host Restarts Session
        print("\n🔄 STEP 4: Host Restarts Session")
        driver.switch_to.window(host_tab)
        restart_session_via_api(token, quiz_id)
        time.sleep(2)
        print("✅ Host restarted session")
        
        # STEP 5: Check Participant Sees Rejoin UI
        print("\n🔍 STEP 5: Check Participant Sees Rejoin UI")
        driver.switch_to.window(participant_tab)
        # Force a fresh poll after restart and allow throttled tab timers to catch up.
        driver.refresh()
        time.sleep(2)

        rejoin_button = None
        deadline = time.time() + 35
        while time.time() < deadline:
            if "/join" in driver.current_url:
                print("✅ Participant auto-navigated to /join")
                rejoin_button = True
                break
            markers = driver.find_elements(
                By.XPATH,
                "//*[contains(., 'Session Restarted') or contains(., 'Restarted') or contains(., 'rejoin')]"
            )
            if markers:
                print(f"✅ Found invalidation marker: '{markers[0].text[:120]}'")
            buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Rejoin') or contains(., 'Join')]")
            if buttons:
                rejoin_button = buttons[0]
                break
            time.sleep(2)

        if not rejoin_button:
            print("❌ FAILED: Could not find session invalidation message/button")
            print(f"Current URL: {driver.current_url}")
            print(f"Page title: {driver.title}")
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text
                print(f"Page snippet: {page_text[:500]}")
            except Exception:
                pass
            return False
        
        # STEP 6: Click Rejoin and Check Navigation
        print("\n🔗 STEP 6: Test Rejoin Navigation")
        try:
            if rejoin_button is not True:
                print("✅ Found rejoin/join button")
                rejoin_button.click()
                time.sleep(2)
            
            current_url = driver.current_url
            print(f"📍 After clicking rejoin: {current_url}")
            
            if "/join" in current_url:
                print("\n" + "="*60)
                print("✅ TEST PASSED: Navigated to /join page")
                print("="*60 + "\n")
                success = True
            elif "/login" in current_url:
                print("\n" + "="*60)
                print("❌ TEST FAILED: Navigated to /login page (should be /join)")
                print("="*60 + "\n")
                success = False
            else:
                print(f"\n⚠️  UNEXPECTED: Navigated to {current_url}")
                success = False
                
        except Exception as e:
            print(f"❌ FAILED: Could not find or click rejoin button: {e}")
            success = False
        
        # Keep browser open for visual inspection
        print("\n⏳ Keeping browser open for 10 seconds for visual inspection...")
        print(f"📺 VNC viewer: http://localhost:7900 (password: secret)")
        time.sleep(10)
        
        return success
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

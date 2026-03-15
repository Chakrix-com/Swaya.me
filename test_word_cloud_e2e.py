#!/usr/bin/env python3
"""
E2E Test for Word Cloud Question Flow
Tests: Create Word Cloud Quiz → Start Session → Join → Advance → Display → Submit
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

BASE_URL = os.getenv("APP_BASE_URL", "https://www.swaya.me")
API_BASE_URL = os.getenv("BASE_URL", f"{BASE_URL}/api/v1")
SELENIUM_URL = os.getenv("SELENIUM_URL", "http://localhost:4444/wd/hub")
TIMEOUT = 15

# Test credentials
EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")

def log(message, level="INFO"):
    colors = {"INFO": "\033[94m", "SUCCESS": "\033[92m", "ERROR": "\033[91m", "WARN": "\033[93m"}
    print(f"{colors.get(level, '')}[{level}] {message}\033[0m")

def setup_driver(name="host"):
    """Setup Chrome driver via Selenium Grid"""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Remote(
        command_executor=SELENIUM_URL,
        options=options
    )
    driver.set_page_load_timeout(30)
    log(f"Driver '{name}' initialized", "SUCCESS")
    return driver

def wait_for_element(driver, by, value, timeout=TIMEOUT, name="element"):
    """Wait for element to be present and visible"""
    try:
        log(f"Waiting for {name}: {value}")
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        log(f"Found {name}", "SUCCESS")
        return element
    except TimeoutException:
        log(f"Timeout waiting for {name}: {value}", "ERROR")
        # Take screenshot for debugging
        driver.save_screenshot(f"/tmp/timeout_{name.replace(' ', '_')}.png")
        raise

def wait_for_any(driver, locators, timeout=TIMEOUT, clickable=False, name="element"):
    """Try multiple locators and return first match."""
    for by, value in locators:
        try:
            log(f"Waiting for {name}: {value}")
            condition = EC.element_to_be_clickable((by, value)) if clickable else EC.presence_of_element_located((by, value))
            element = WebDriverWait(driver, timeout).until(condition)
            log(f"Found {name}", "SUCCESS")
            return element
        except TimeoutException:
            continue
    log(f"Timeout waiting for any locator for {name}", "ERROR")
    driver.save_screenshot(f"/tmp/timeout_{name.replace(' ', '_')}.png")
    raise TimeoutException(f"No locator matched for {name}")

def safe_quit(driver):
    if not driver:
        return
    try:
        driver.quit()
    except Exception:
        pass

def api_login():
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        verify=False,
        timeout=20
    )
    response.raise_for_status()
    return response.json()["access_token"]

def find_ready_wordcloud_quiz(token):
    headers = {"Authorization": f"Bearer {token}"}
    quizzes_resp = requests.get(f"{API_BASE_URL}/quizzes/", headers=headers, verify=False, timeout=20)
    quizzes_resp.raise_for_status()
    for quiz in quizzes_resp.json():
        if str(quiz.get("status", "")).lower() != "ready":
            continue
        quiz_id = quiz["id"]
        detail_resp = requests.get(f"{API_BASE_URL}/quizzes/{quiz_id}", headers=headers, verify=False, timeout=20)
        if detail_resp.status_code != 200:
            continue
        questions = detail_resp.json().get("questions", [])
        if any(q.get("question_type") == "word_cloud" for q in questions):
            return quiz_id
    raise RuntimeError("No READY quiz with word_cloud question found")

def cleanup_open_sessions(token, quiz_id):
    headers = {"Authorization": f"Bearer {token}"}
    sessions_resp = requests.get(f"{API_BASE_URL}/quizzes/{quiz_id}/sessions", headers=headers, verify=False, timeout=20)
    if sessions_resp.status_code != 200:
        return
    for session in sessions_resp.json().get("sessions", []):
        if session.get("status") in ("active", "created"):
            requests.post(f"{API_BASE_URL}/quizzes/sessions/{session['id']}/end", headers=headers, verify=False, timeout=20)

def test_word_cloud_flow():
    """Test complete word cloud question flow"""
    host = None
    
    try:
        log("=== Starting Word Cloud E2E Test ===", "INFO")
        token = api_login()
        quiz_id = find_ready_wordcloud_quiz(token)
        cleanup_open_sessions(token, quiz_id)
        
        # Step 1: Host Login
        log("\n--- STEP 1: Host Login ---", "INFO")
        host = setup_driver("host")
        host.get(f"{BASE_URL}/login")
        time.sleep(2)

        email_input = wait_for_any(host, [
            (By.ID, "login_email"),
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='Email' i]"),
            (By.CSS_SELECTOR, "input[autocomplete='username']")
        ], name="email input")
        email_input.send_keys(EMAIL)

        password_input = wait_for_any(host, [
            (By.ID, "login_password"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']")
        ], name="password input")
        password_input.send_keys(PASSWORD)

        login_btn = wait_for_any(host, [
            (By.XPATH, "//button[contains(., 'Login')]"),
            (By.CSS_SELECTOR, "button[type='submit']")
        ], clickable=True, name="login button")
        login_btn.click()
        WebDriverWait(host, 15).until(lambda d: "/dashboard" in d.current_url or "/quiz/" in d.current_url)
        log("Host logged in successfully", "SUCCESS")
        
        # Step 2: Navigate to selected quiz control
        log("\n--- STEP 2: Navigate to Quiz ---", "INFO")
        host.get(f"{BASE_URL}/quiz/{quiz_id}/control")
        time.sleep(2)
        log(f"Navigated to quiz {quiz_id} control", "SUCCESS")
        
        # Step 3: Start Session
        log("\n--- STEP 3: Start Session ---", "INFO")
        start_btn = wait_for_element(host, By.XPATH, "//button[contains(., 'Start Session')]", 
                                     timeout=10, name="start session button")
        start_btn.click()
        time.sleep(3)
        
        # Get join code
        join_code_elem = wait_for_any(host, [
            (By.XPATH, "//*[contains(text(), 'Join Code')]/following::*[1]"),
            (By.CSS_SELECTOR, ".join-code"),
            (By.CSS_SELECTOR, "code"),
            (By.XPATH, "//div[contains(@class, 'ant-statistic-content')]")
        ], timeout=15, name="join code")
        join_code = join_code_elem.text.strip()
        log(f"Session started with join code: {join_code}", "SUCCESS")
        
        # Step 4: Advance to first question
        log("\n--- STEP 4: Advance to Question ---", "INFO")
        try:
            advance_btn = wait_for_any(host, [
                (By.XPATH, "//button[contains(., 'Start First Question')]"),
                (By.XPATH, "//button[contains(., 'Next')]"),
                (By.XPATH, "//button[contains(., 'Advance')]"),
                (By.XPATH, "//button[contains(., 'Next Question')]")
            ], timeout=12, clickable=True, name="advance button")
            advance_btn.click()
            time.sleep(2)
            log("Advanced to first question", "SUCCESS")
        except TimeoutException:
            log("No advance button found, continuing with current session state", "WARN")
        
        # Check what question is displayed on host screen
        time.sleep(2)
        page_text = host.find_element(By.TAG_NAME, "body").text
        log(f"Host screen contains: {page_text[:200]}", "INFO")
        
        # Step 5: Audience joins
        log("\n--- STEP 5: Audience Joins ---", "INFO")
        host.execute_script("window.open('');")
        host.switch_to.window(host.window_handles[-1])
        audience = host
        audience.get(f"{BASE_URL}/join")
        time.sleep(2)
        
        code_input = wait_for_any(audience, [
            (By.ID, "join_join_code"),
            (By.NAME, "join_code"),
            (By.CSS_SELECTOR, "input[inputmode='numeric']"),
            (By.CSS_SELECTOR, "input[placeholder*='code' i]")
        ], timeout=10, name="join code input")
        code_input.send_keys(join_code)

        name_input = wait_for_any(audience, [
            (By.ID, "join_display_name"),
            (By.NAME, "display_name"),
            (By.CSS_SELECTOR, "input[placeholder*='name' i]"),
            (By.CSS_SELECTOR, "input[id*='display' i]")
        ], timeout=10, name="display name input")
        name_input.send_keys("Test User")
        
        join_btn = wait_for_element(audience, By.XPATH, "//button[contains(., 'Join')]",
                                   timeout=10, name="join button")
        join_btn.click()
        time.sleep(3)
        
        log("Audience joined session", "SUCCESS")
        
        # Step 6: Check if question is displayed
        log("\n--- STEP 6: Verify Question Display ---", "INFO")
        time.sleep(3)
        
        # Take screenshot for debugging
        audience.save_screenshot("/tmp/audience_screen.png")
        log("Screenshot saved to /tmp/audience_screen.png", "INFO")
        
        # Check page content
        audience_body = audience.find_element(By.TAG_NAME, "body")
        audience_text = audience_body.text
        log(f"Audience screen text: {audience_text[:300]}", "INFO")
        
        # Check for different possible states
        if "Waiting for host" in audience_text:
            log("Audience is stuck on 'Waiting for host' screen", "ERROR")
            log("This means current_question is NULL or not being sent correctly", "ERROR")
            
            # Check network requests via browser console
            logs = audience.get_log('browser')
            for entry in logs[-20:]:
                log(f"Browser log: {entry}", "INFO")
            
            raise Exception("Question not displayed - stuck on waiting screen")
        
        # Look for word cloud UI elements
        try:
            textarea = audience.find_element(By.TAG_NAME, "textarea")
            log("Found textarea - Word Cloud UI is displayed!", "SUCCESS")
            
            # Check for purple badge
            if "Word Cloud" in audience_text:
                log("Found 'Word Cloud' badge", "SUCCESS")
            
            # Step 7: Submit answer
            log("\n--- STEP 7: Submit Answer ---", "INFO")
            textarea.send_keys("Testing word cloud")
            time.sleep(1)
            
            submit_btn = wait_for_element(audience, By.XPATH, "//button[contains(., 'Submit')]",
                                         timeout=5, name="submit button")
            submit_btn.click()
            time.sleep(2)
            
            log("Answer submitted successfully", "SUCCESS")
            
            # Check for success message
            if "Answer Submitted" in audience.find_element(By.TAG_NAME, "body").text:
                log("Submission confirmed", "SUCCESS")
            
        except NoSuchElementException:
            log("Word Cloud UI (textarea) not found", "ERROR")
            
            # Check if it's showing MCQ UI instead
            if "option_a" in audience_text or audience.find_elements(By.XPATH, "//input[@type='radio']"):
                log("ERROR: Showing MCQ UI instead of Word Cloud UI", "ERROR")
                log("question_type is not being sent or recognized", "ERROR")
            
            raise Exception("Word Cloud UI not displayed")
        
        log("\n=== Test Completed Successfully ===", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"Test failed: {str(e)}", "ERROR")
        
        # Debug output
        if host:
            try:
                log(f"Host URL: {host.current_url}", "INFO")
                host.save_screenshot("/tmp/host_error.png")
            except Exception:
                pass
        if 'audience' in locals() and audience:
            try:
                log(f"Audience URL: {audience.current_url}", "INFO")
                audience.save_screenshot("/tmp/audience_error.png")
            except Exception:
                pass
        
        return False
        
    finally:
        safe_quit(host)

if __name__ == "__main__":
    # Use existing Selenium container on port 4444
    print("Using existing Selenium container on localhost:4444...")
    print("VNC viewer available at: http://localhost:7900 (password: secret)")
    
    time.sleep(2)
    
    success = test_word_cloud_flow()
    sys.exit(0 if success else 1)

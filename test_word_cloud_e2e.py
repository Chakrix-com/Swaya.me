#!/usr/bin/env python3
"""
E2E Test for Word Cloud Question Flow
Tests: Create Word Cloud Quiz → Start Session → Join → Advance → Display → Submit
"""
import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = "https://www.swaya.me"
SELENIUM_URL = "http://localhost:4444/wd/hub"
TIMEOUT = 15

# Test credentials
EMAIL = "vinaykakade@gmail.com"
PASSWORD = "Swaya@Me2025"

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

def test_word_cloud_flow():
    """Test complete word cloud question flow"""
    host = None
    audience = None
    
    try:
        log("=== Starting Word Cloud E2E Test ===", "INFO")
        
        # Step 1: Host Login
        log("\n--- STEP 1: Host Login ---", "INFO")
        host = setup_driver("host")
        host.get(f"{BASE_URL}/login")
        time.sleep(2)
        
        email_input = wait_for_element(host, By.NAME, "email", name="email input")
        email_input.send_keys(EMAIL)
        
        password_input = wait_for_element(host, By.NAME, "password", name="password input")
        password_input.send_keys(PASSWORD)
        
        login_btn = wait_for_element(host, By.XPATH, "//button[contains(., 'Login')]", name="login button")
        login_btn.click()
        
        wait_for_element(host, By.XPATH, "//h1[contains(., 'Dashboard')] | //h2[contains(., 'Dashboard')]", 
                        timeout=10, name="dashboard")
        log("Host logged in successfully", "SUCCESS")
        
        # Step 2: Find a quiz with word cloud questions
        log("\n--- STEP 2: Navigate to Quiz ---", "INFO")
        host.get(f"{BASE_URL}/dashboard")
        time.sleep(2)
        
        # Find "Another Quiz" or any quiz
        quiz_cards = host.find_elements(By.XPATH, "//div[contains(@class, 'ant-card')]")
        log(f"Found {len(quiz_cards)} quizzes", "INFO")
        
        # Look for "Another Quiz" or first READY quiz
        target_quiz = None
        for card in quiz_cards:
            if "Another Quiz" in card.text or "READY" in card.text:
                target_quiz = card
                break
        
        if not target_quiz:
            log("No suitable quiz found, using first quiz", "WARN")
            target_quiz = quiz_cards[0] if quiz_cards else None
        
        if not target_quiz:
            raise Exception("No quizzes found")
        
        log(f"Quiz card text: {target_quiz.text[:100]}", "INFO")
        
        # Click "Control" button to start session
        control_btn = target_quiz.find_element(By.XPATH, ".//button[contains(., 'Control')]")
        control_btn.click()
        time.sleep(2)
        
        log("Navigated to Quiz Control", "SUCCESS")
        
        # Step 3: Start Session
        log("\n--- STEP 3: Start Session ---", "INFO")
        start_btn = wait_for_element(host, By.XPATH, "//button[contains(., 'Start Session')]", 
                                     timeout=10, name="start session button")
        start_btn.click()
        time.sleep(3)
        
        # Get join code
        join_code_elem = wait_for_element(host, By.XPATH, 
                                         "//*[contains(text(), 'Join Code:')]/following-sibling::* | //*[contains(@class, 'join-code')] | //code",
                                         timeout=10, name="join code")
        join_code = join_code_elem.text.strip()
        log(f"Session started with join code: {join_code}", "SUCCESS")
        
        # Step 4: Advance to first question
        log("\n--- STEP 4: Advance to Question ---", "INFO")
        advance_btn = wait_for_element(host, By.XPATH, "//button[contains(., 'Next')] | //button[contains(., 'Advance')]",
                                      timeout=10, name="advance button")
        advance_btn.click()
        time.sleep(2)
        log("Advanced to first question", "SUCCESS")
        
        # Check what question is displayed on host screen
        time.sleep(2)
        page_text = host.find_element(By.TAG_NAME, "body").text
        log(f"Host screen contains: {page_text[:200]}", "INFO")
        
        # Step 5: Audience joins
        log("\n--- STEP 5: Audience Joins ---", "INFO")
        audience = setup_driver("audience")
        audience.get(f"{BASE_URL}/join")
        time.sleep(2)
        
        code_input = wait_for_element(audience, By.XPATH, "//input[@placeholder='Enter code']", 
                                     timeout=10, name="join code input")
        code_input.send_keys(join_code)
        
        name_input = wait_for_element(audience, By.XPATH, "//input[@placeholder='Your name']",
                                     timeout=10, name="display name input")
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
            log(f"Host URL: {host.current_url}", "INFO")
            host.save_screenshot("/tmp/host_error.png")
        if audience:
            log(f"Audience URL: {audience.current_url}", "INFO")
            audience.save_screenshot("/tmp/audience_error.png")
        
        return False
        
    finally:
        if host:
            host.quit()
        if audience:
            audience.quit()

if __name__ == "__main__":
    # Use existing Selenium container on port 4444
    print("Using existing Selenium container on localhost:4444...")
    print("VNC viewer available at: http://localhost:7900 (password: secret)")
    
    time.sleep(2)
    
    success = test_word_cloud_flow()
    sys.exit(0 if success else 1)

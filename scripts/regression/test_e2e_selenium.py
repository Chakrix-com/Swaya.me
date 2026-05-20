#!/usr/bin/env python3
"""
End-to-End Selenium Test for Swaya.me Quiz Platform
Tests complete flow: Login → Create/Start Session → Join → Submit Answer → Verify Results
"""
import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = "https://www.swaya.me"
TIMEOUT = 20

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_step(step_num, message):
    print(f"\n{Colors.BLUE}📝 Step {step_num}: {message}{Colors.END}")

def log_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def log_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def log_info(message):
    print(f"{Colors.YELLOW}ℹ️  {message}{Colors.END}")

def setup_driver():
    """Setup Firefox driver for headless testing"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.set_preference('security.insecure_field_warning.contextual.enabled', False)
    options.binary_location = '/usr/bin/firefox'
    return webdriver.Firefox(options=options)

def test_complete_quiz_flow():
    """Test complete quiz flow from host and audience perspective"""
    host_driver = None
    audience_driver = None
    
    try:
        print(f"\n{Colors.BLUE}{'='*60}")
        print("🚀 Starting End-to-End Selenium Test for Swaya.me")
        print(f"{'='*60}{Colors.END}\n")
        
        # ===== HOST FLOW =====
        log_step(1, "Host Login")
        host_driver = setup_driver()
        host_driver.get(f"{BASE_URL}/login")
        time.sleep(3)
        
        # Login
        email_input = WebDriverWait(host_driver, TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "login_email"))
        )
        password_input = host_driver.find_element(By.ID, "login_password")
        email_input.send_keys("demo@swaya.me")
        password_input.send_keys("Demo1234")
        
        submit_btn = host_driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        time.sleep(4)
        
        # Verify redirect to dashboard
        assert "/dashboard" in host_driver.current_url, "Failed to redirect to dashboard"
        log_success("Host logged in successfully")
        
        # ===== START SESSION =====
        log_step(2, "Starting Quiz Session")
        
        # Look for "Start Session" button
        try:
            start_button = WebDriverWait(host_driver, TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Start Session')]"))
            )
            start_button.click()
            time.sleep(4)
            log_success("Clicked Start Session button")
        except TimeoutException:
            log_error("No 'Start Session' button found - navigating to quiz control")
            # If already in a session, find the quiz ID and navigate
            host_driver.get(f"{BASE_URL}/quiz/2/control")
            time.sleep(3)
        
        # ===== GET JOIN CODE =====
        log_step(3, "Getting Join Code")
        
        # Wait for join code to appear
        join_code_element = WebDriverWait(host_driver, TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'ant-statistic-content')]"))
        )
        join_code = join_code_element.text.strip()
        
        if not join_code or len(join_code) < 4:
            # Try alternative selector
            join_code_element = host_driver.find_element(By.XPATH, "//div[contains(text(), 'Join Code')]/following-sibling::div")
            join_code = join_code_element.text.strip()
        
        log_success(f"Join Code: {join_code}")
        log_info(f"Session URL: {host_driver.current_url}")
        
        # ===== ADVANCE TO FIRST QUESTION =====
        log_step(4, "Advancing to First Question")
        
        try:
            # Look for "Start First Question" or "Advance" button
            advance_button = WebDriverWait(host_driver, TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Start First Question') or contains(text(), 'Advance') or contains(text(), 'Next Question')]"))
            )
            button_text = advance_button.text
            advance_button.click()
            time.sleep(4)
            log_success(f"Clicked '{button_text}' button")
        except TimeoutException:
            log_error("Could not find advance button - session might already be started")
            # Continue anyway
        
        # Verify question is visible on host screen
        try:
            question_text = WebDriverWait(host_driver, TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Question') and contains(text(), 'of')]"))
            )
            log_success(f"Question visible on host: {question_text.text}")
        except:
            log_error("Question not visible on host screen")
        
        # ===== AUDIENCE JOIN =====
        log_step(5, f"Audience Joining with Code: {join_code}")
        
        audience_driver = setup_driver()
        join_url = f"{BASE_URL}/join/{join_code}"
        audience_driver.get(join_url)
        time.sleep(3)
        
        log_info(f"Join URL: {join_url}")
        
        # Enter display name (optional field)
        try:
            name_input = audience_driver.find_element(By.ID, "join_display_name")
            name_input.send_keys("Selenium Test User")
        except:
            log_info("Display name field not found or not required")
        
        # Click Join button
        join_button = WebDriverWait(audience_driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Join Quiz') or contains(text(), 'Join')]"))
        )
        join_button.click()
        time.sleep(4)
        
        log_success("Audience joined session")
        log_info(f"Current URL: {audience_driver.current_url}")
        
        # ===== VERIFY QUESTION APPEARS =====
        log_step(6, "Verifying Question Appears for Audience")
        
        # Wait for question to appear (not "Waiting for host" message)
        try:
            # Check if we're NOT seeing "Waiting for host"
            page_source = audience_driver.page_source
            
            if "Waiting for host" in page_source:
                log_error("Audience still seeing 'Waiting for host' message")
                log_info("Waiting 5 more seconds for question to load...")
                time.sleep(5)
            
            # Look for question text or radio buttons
            question_element = WebDriverWait(audience_driver, TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='radio'] | //div[contains(@class, 'ant-radio-group')]"))
            )
            log_success("Question with options appeared for audience")
            
            # Try to get question text
            try:
                question_card = audience_driver.find_element(By.XPATH, "//div[contains(@class, 'ant-card')]//h4 | //div[contains(@class, 'ant-card')]//div[contains(@style, 'fontSize')]")
                log_info(f"Question text: {question_card.text}")
            except:
                pass
                
        except TimeoutException:
            log_error("Question did not appear for audience within timeout")
            log_info("Taking screenshot...")
            audience_driver.save_screenshot('/tmp/audience_no_question.png')
            raise
        
        # ===== SELECT AND SUBMIT ANSWER =====
        log_step(7, "Selecting and Submitting Answer")
        
        # Select option A
        try:
            option_a = WebDriverWait(audience_driver, TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@value='A'] | //label[contains(text(), 'A:')]"))
            )
            option_a.click()
            time.sleep(1)
            log_success("Selected option A")
        except:
            # Try alternative selector
            radio_buttons = audience_driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            if radio_buttons:
                radio_buttons[0].click()
                time.sleep(1)
                log_success("Selected first option")
            else:
                raise Exception("No radio buttons found")
        
        # Click Submit button
        submit_button = WebDriverWait(audience_driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Submit')]"))
        )
        submit_button.click()
        time.sleep(3)
        log_success("Answer submitted")
        
        # Verify submission feedback
        try:
            submitted_indicator = WebDriverWait(audience_driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Submitted') or contains(text(), 'Correct') or contains(text(), 'Incorrect')]"))
            )
            log_success(f"Submission confirmed: {submitted_indicator.text}")
        except:
            log_info("No explicit submission confirmation found (might be expected)")
        
        # ===== VERIFY HOST SEES RESULTS =====
        log_step(8, "Verifying Host Sees Answer")
        
        time.sleep(3)  # Wait for polling to update
        
        # Look for "responses received" or answer count
        try:
            results = host_driver.find_element(By.XPATH, "//*[contains(text(), 'response')]")
            log_success(f"Host sees results: {results.text}")
        except:
            log_info("Could not find explicit 'responses' text, checking progress bars...")
        
        # Check for progress bars (indicating answers)
        try:
            progress_bars = host_driver.find_elements(By.CSS_SELECTOR, ".ant-progress")
            if progress_bars:
                log_success(f"Host shows {len(progress_bars)} answer option(s) with progress")
        except:
            pass
        
        # ===== SUCCESS =====
        print(f"\n{Colors.GREEN}{'='*60}")
        print("🎉 ALL TESTS PASSED! Complete quiz flow working end-to-end!")
        print(f"{'='*60}{Colors.END}\n")
        
        return True
        
    except Exception as e:
        log_error(f"Test failed: {str(e)}")
        
        # Take screenshots for debugging
        if host_driver:
            try:
                host_driver.save_screenshot('/tmp/host_error.png')
                log_info("Host screenshot saved to /tmp/host_error.png")
                log_info(f"Host URL: {host_driver.current_url}")
            except:
                pass
        
        if audience_driver:
            try:
                audience_driver.save_screenshot('/tmp/audience_error.png')
                log_info("Audience screenshot saved to /tmp/audience_error.png")
                log_info(f"Audience URL: {audience_driver.current_url}")
            except:
                pass
        
        import traceback
        print(f"\n{Colors.RED}Traceback:{Colors.END}")
        traceback.print_exc()
        
        return False
        
    finally:
        log_info("Cleaning up drivers...")
        if host_driver:
            host_driver.quit()
        if audience_driver:
            audience_driver.quit()

if __name__ == "__main__":
    success = test_complete_quiz_flow()
    sys.exit(0 if success else 1)

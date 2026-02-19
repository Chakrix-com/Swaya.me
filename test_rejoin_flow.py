#!/usr/bin/env python3
"""
E2E Test: Session Invalidation & Rejoin Flow
Tests that when a host restarts a session, participants see the rejoin UI
and can navigate to /join page (not /login)
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time

# Configuration
SELENIUM_URL = "http://localhost:4444/wd/hub"
APP_URL = "https://www.swaya.me"
HOST_EMAIL = "demo@swaya.me"
HOST_PASSWORD = "Demo1234"

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

def host_login_and_start_session(driver):
    """Login as host and start the first quiz session"""
    print("🔑 Host: Logging in...")
    driver.get(f"{APP_URL}/login")
    
    # Login
    wait = WebDriverWait(driver, 10)
    email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    email_input.send_keys(HOST_EMAIL)
    
    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_input.send_keys(HOST_PASSWORD)
    password_input.send_keys(Keys.RETURN)
    
    # Wait for dashboard
    time.sleep(2)
    print("✅ Host: Logged in successfully")
    
    # Click "Start Quiz" on first quiz
    print("🎯 Host: Starting quiz session...")
    start_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start Quiz')]")))
    start_button.click()
    time.sleep(1)
    
    # Click "Start Session" button
    start_session_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start Session')]")))
    start_session_btn.click()
    time.sleep(2)
    
    # Get the join code or link
    join_code_element = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Join Code:')]/following-sibling::*")))
    join_code = join_code_element.text.strip()
    print(f"📋 Join Code: {join_code}")
    
    return join_code

def participant_join_session(driver, join_code):
    """Join session as participant"""
    print(f"👥 Participant: Joining with code {join_code}...")
    driver.get(f"{APP_URL}/join")
    
    wait = WebDriverWait(driver, 10)
    
    # Enter display name
    name_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='name' i], input[id*='display' i]")))
    name_input.send_keys("Test Participant")
    
    # Enter join code
    code_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='code' i], input[id*='join' i]")
    code_input.clear()
    code_input.send_keys(join_code)
    
    # Click join button
    join_button = driver.find_element(By.XPATH, "//button[contains(., 'Join')]")
    join_button.click()
    
    time.sleep(2)
    print("✅ Participant: Joined session")

def host_restart_session(driver):
    """Host ends and restarts the session"""
    print("🔄 Host: Restarting session...")
    
    wait = WebDriverWait(driver, 10)
    
    # Click "End Session" button
    end_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'End Session')]")))
    end_button.click()
    time.sleep(1)
    
    # Click "Start Session" again
    start_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start Session')]")))
    start_button.click()
    time.sleep(2)
    
    print("✅ Host: Session restarted")

def check_participant_sees_rejoin_ui(driver):
    """Verify participant sees the rejoin UI (not waiting screen)"""
    print("🔍 Participant: Checking for session invalidation UI...")
    
    wait = WebDriverWait(driver, 10)
    
    # Should see "Session Restarted" or similar message
    try:
        rejoin_msg = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Restarted') or contains(text(), 'rejoin') i]")))
        print(f"✅ Participant: Sees invalidation message: '{rejoin_msg.text}'")
    except:
        print("❌ Participant: Could not find session invalidation message")
        return False
    
    # Should see "Rejoin Quiz" button
    try:
        rejoin_button = driver.find_element(By.XPATH, "//button[contains(., 'Rejoin')]")
        print("✅ Participant: Found 'Rejoin Quiz' button")
        return rejoin_button
    except:
        print("❌ Participant: Could not find 'Rejoin Quiz' button")
        return None

def test_rejoin_navigation(driver, rejoin_button):
    """Click rejoin button and verify navigation to /join (not /login)"""
    print("🔗 Participant: Clicking 'Rejoin Quiz' button...")
    
    rejoin_button.click()
    time.sleep(2)
    
    current_url = driver.current_url
    print(f"📍 Current URL: {current_url}")
    
    if "/join" in current_url:
        print("✅ SUCCESS: Navigated to /join page (CORRECT)")
        return True
    elif "/login" in current_url:
        print("❌ FAILURE: Navigated to /login page (INCORRECT)")
        return False
    else:
        print(f"⚠️  UNEXPECTED: Navigated to {current_url}")
        return False

def main():
    """Run the complete rejoin flow test"""
    host_driver = None
    participant_driver = None
    
    try:
        print("\n" + "="*60)
        print("🧪 E2E TEST: Session Invalidation & Rejoin Flow")
        print("="*60 + "\n")
        
        # Setup two browser instances
        print("🌐 Setting up browsers...")
        host_driver = setup_driver()
        participant_driver = setup_driver()
        
        # Step 1: Host starts session
        join_code = host_login_and_start_session(host_driver)
        
        # Step 2: Participant joins
        participant_join_session(participant_driver, join_code)
        
        # Step 3: Host restarts session (invalidates participant)
        host_restart_session(host_driver)
        
        # Give time for participant to receive invalidation
        time.sleep(3)
        
        # Step 4: Check participant sees rejoin UI
        rejoin_button = check_participant_sees_rejoin_ui(participant_driver)
        
        if not rejoin_button:
            print("\n❌ TEST FAILED: Participant does not see rejoin UI")
            return False
        
        # Step 5: Test rejoin navigation
        success = test_rejoin_navigation(participant_driver, rejoin_button)
        
        print("\n" + "="*60)
        if success:
            print("✅ TEST PASSED: Rejoin button navigates to /join")
        else:
            print("❌ TEST FAILED: Rejoin button does not navigate to /join")
        print("="*60 + "\n")
        
        # Keep browsers open for 10 seconds for visual inspection
        print("⏳ Keeping browsers open for 10 seconds...")
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
        if host_driver:
            host_driver.quit()
        if participant_driver:
            participant_driver.quit()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

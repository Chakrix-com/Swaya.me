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

def main():
    """Run the simplified rejoin flow test"""
    driver = None
    
    try:
        print("\n" + "="*60)
        print("🧪 E2E TEST: Session Invalidation & Rejoin Flow")
        print("="*60 + "\n")
        
        # Setup browser
        print("🌐 Setting up browser...")
        driver = setup_driver()
        wait = WebDriverWait(driver, 10)
        
        # STEP 1: Host Login
        print("\n🔑 STEP 1: Host Login")
        driver.get(f"{APP_URL}/login")
        time.sleep(1)
        
        email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
        email_input.send_keys(HOST_EMAIL)
        
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_input.send_keys(HOST_PASSWORD)
        password_input.send_keys(Keys.RETURN)
        time.sleep(2)
        print("✅ Host logged in")
        
        # STEP 2: Start Quiz Session
        print("\n🎯 STEP 2: Start Quiz Session")
        start_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start Quiz')]")))
        start_button.click()
        time.sleep(1)
        
        start_session_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start Session')]")))
        start_session_btn.click()
        time.sleep(2)
        
        # Get join code
        join_code_element = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Join Code:')]/following-sibling::*")))
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
        time.sleep(1)
        
        name_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='name' i], input[id*='display' i]")))
        name_input.send_keys("Test Participant")
        
        code_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='code' i], input[id*='join' i]")
        code_input.clear()
        code_input.send_keys(join_code)
        
        join_button = driver.find_element(By.XPATH, "//button[contains(., 'Join')]")
        join_button.click()
        time.sleep(2)
        print("✅ Participant joined session")
        
        # STEP 4: Host Restarts Session
        print("\n🔄 STEP 4: Host Restarts Session")
        driver.switch_to.window(host_tab)
        time.sleep(1)
        
        end_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'End Session')]")))
        end_button.click()
        time.sleep(1)
        
        start_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start Session')]")))
        start_button.click()
        time.sleep(2)
        print("✅ Host restarted session")
        
        # STEP 5: Check Participant Sees Rejoin UI
        print("\n🔍 STEP 5: Check Participant Sees Rejoin UI")
        driver.switch_to.window(participant_tab)
        time.sleep(3)  # Wait for polling to detect invalidation
        
        try:
            rejoin_msg = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Restarted') or contains(text(), 'rejoin')]")))
            print(f"✅ Found invalidation message: '{rejoin_msg.text}'")
        except:
            print("❌ FAILED: Could not find session invalidation message")
            print(f"Current URL: {driver.current_url}")
            print(f"Page title: {driver.title}")
            return False
        
        # STEP 6: Click Rejoin and Check Navigation
        print("\n🔗 STEP 6: Test Rejoin Navigation")
        try:
            rejoin_button = driver.find_element(By.XPATH, "//button[contains(., 'Rejoin')]")
            print("✅ Found 'Rejoin Quiz' button")
            
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

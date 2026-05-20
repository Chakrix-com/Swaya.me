#!/usr/bin/env python3
"""
End-to-End Test for Swaya.me Quiz Flow
Tests: Login → Start Session → Join as Audience → Submit Answer → View Results
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

BASE_URL = "https://www.swaya.me"

def setup_driver(headless=False):
    """Setup Chrome driver"""
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--ignore-certificate-errors')
    return webdriver.Chrome(options=options)

def test_quiz_flow():
    """Test complete quiz flow"""
    host_driver = None
    audience_driver = None
    
    try:
        print("🚀 Starting End-to-End Quiz Test...")
        
        # Step 1: Host Login
        print("\n📝 Step 1: Host Login")
        host_driver = setup_driver()
        host_driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        
        email_input = host_driver.find_element(By.ID, "login_email")
        password_input = host_driver.find_element(By.ID, "login_password")
        email_input.send_keys("demo@swaya.me")
        password_input.send_keys("Demo1234")
        
        submit_btn = host_driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        time.sleep(3)
        
        print("✅ Host logged in successfully")
        
        # Step 2: Navigate to existing quiz and start session
        print("\n📝 Step 2: Starting Quiz Session")
        host_driver.get(f"{BASE_URL}/dashboard")
        time.sleep(2)
        
        # Find the first quiz and click "Start Session"
        start_buttons = host_driver.find_elements(By.XPATH, "//button[contains(text(), 'Start Session')]")
        if not start_buttons:
            print("❌ No 'Start Session' button found. Please create a quiz first.")
            return False
        
        start_buttons[0].click()
        time.sleep(3)
        
        # Wait for session to start and get join code
        join_code_elem = WebDriverWait(host_driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'ant-statistic')]//div[contains(@class, 'ant-statistic-content')]"))
        )
        join_code = join_code_elem.text.strip()
        print(f"✅ Session started! Join Code: {join_code}")
        
        # Step 3: Advance to first question
        print("\n📝 Step 3: Advancing to First Question")
        advance_btn = WebDriverWait(host_driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Start First Question') or contains(text(), 'Advance')]"))
        )
        advance_btn.click()
        time.sleep(3)
        print("✅ Advanced to first question")
        
        # Step 4: Audience joins session
        print(f"\n📝 Step 4: Audience Joining with code: {join_code}")
        audience_driver = setup_driver()
        audience_driver.get(f"{BASE_URL}/join/{join_code}")
        time.sleep(2)
        
        # Enter display name
        name_input = audience_driver.find_element(By.ID, "join_display_name")
        name_input.send_keys("Test Participant")
        
        join_btn = audience_driver.find_element(By.XPATH, "//button[contains(text(), 'Join Quiz')]")
        join_btn.click()
        time.sleep(3)
        print("✅ Audience joined successfully")
        
        # Step 5: Verify question appears for audience
        print("\n📝 Step 5: Checking if Question Appears for Audience")
        question_elem = WebDriverWait(audience_driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Question')]"))
        )
        print(f"✅ Question visible to audience: {question_elem.text}")
        
        # Step 6: Audience submits answer
        print("\n📝 Step 6: Submitting Answer")
        # Select option A
        option_a = audience_driver.find_element(By.XPATH, "//input[@value='A']")
        option_a.click()
        time.sleep(1)
        
        submit_btn = audience_driver.find_element(By.XPATH, "//button[contains(text(), 'Submit Answer')]")
        submit_btn.click()
        time.sleep(2)
        print("✅ Answer submitted")
        
        # Step 7: Verify answer appears on host screen
        print("\n📝 Step 7: Checking Host Screen for Results")
        time.sleep(3)  # Wait for polling
        
        # Look for answer count on host screen
        results_elem = host_driver.find_element(By.XPATH, "//div[contains(text(), 'responses received')]")
        print(f"✅ Host sees results: {results_elem.text}")
        
        print("\n🎉 All tests passed! Quiz flow is working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Take screenshots for debugging
        try:
            if host_driver:
                host_driver.save_screenshot('/tmp/host_error.png')
                print("📸 Host screenshot saved to /tmp/host_error.png")
        except:
            pass
        
        try:
            if audience_driver:
                audience_driver.save_screenshot('/tmp/audience_error.png')
                print("📸 Audience screenshot saved to /tmp/audience_error.png")
        except:
            pass
        
        return False
        
    finally:
        print("\n🧹 Cleaning up...")
        if host_driver:
            host_driver.quit()
        if audience_driver:
            audience_driver.quit()

if __name__ == "__main__":
    success = test_quiz_flow()
    exit(0 if success else 1)

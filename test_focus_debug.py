#!/usr/bin/env python3
"""
Debug script to test focus issues in QuizBuilder
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

# Chrome options
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 10)

try:
    print("🔍 Starting focus debugging test...")
    
    # Navigate to login
    print("\n1. Navigating to login page...")
    driver.get("http://localhost:3000/login")
    time.sleep(2)
    
    # Login
    print("2. Logging in...")
    email_input = wait.until(EC.presence_of_element_located((By.ID, "email")))
    email_input.send_keys("demo@swaya.me")
    
    password_input = driver.find_element(By.ID, "password")
    password_input.send_keys("Demo1234")
    
    login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    login_button.click()
    time.sleep(3)
    
    # Navigate to quiz builder (assuming first quiz)
    print("3. Navigating to quiz builder...")
    driver.get("http://localhost:3000/quiz/1/edit")
    time.sleep(3)
    
    # Enable browser console log capture
    print("\n4. Capturing browser console logs...")
    logs = driver.get_log('browser')
    if logs:
        print("  Browser console logs BEFORE clicking Add Question:")
        for log in logs[-10:]:  # Last 10 logs
            print(f"    [{log['level']}] {log['message']}")
    else:
        print("  No console logs yet")
    
    # Click "Add Question" button
    print("\n5. Clicking 'Add Question' button...")
    add_question_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Add Question')]")))
    add_question_btn.click()
    time.sleep(2)
    
    # Check console logs after clicking
    print("\n6. Console logs AFTER clicking Add Question:")
    logs = driver.get_log('browser')
    if logs:
        for log in logs[-20:]:  # Last 20 logs
            print(f"    [{log['level']}] {log['message']}")
    else:
        print("  No new console logs")
    
    # Try to click on question text field
    print("\n7. Attempting to focus question text field...")
    try:
        question_textarea = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder*='question']")))
        print(f"  Found textarea: {question_textarea.get_attribute('placeholder')}")
        
        # Click on it
        question_textarea.click()
        time.sleep(1)
        
        # Check if it's focused
        active_element = driver.switch_to.active_element
        is_focused = (active_element == question_textarea)
        print(f"  Is focused after click: {is_focused}")
        
        if is_focused:
            print("  ✅ Focus is working!")
        else:
            print(f"  ❌ Focus NOT working. Active element: {active_element.tag_name}")
        
        # Try typing
        print("\n8. Attempting to type in textarea...")
        question_textarea.send_keys("Test")
        time.sleep(0.5)
        
        value = question_textarea.get_attribute('value')
        print(f"  Value after typing 'Test': '{value}'")
        
        # Wait a bit and check again
        time.sleep(1)
        active_element = driver.switch_to.active_element
        is_still_focused = (active_element == question_textarea)
        print(f"  Is STILL focused after typing: {is_still_focused}")
        
    except TimeoutException:
        print("  ❌ Could not find question textarea")
    
    # Check console logs after interaction
    print("\n9. Console logs AFTER interaction:")
    logs = driver.get_log('browser')
    if logs:
        for log in logs[-20:]:
            print(f"    [{log['level']}] {log['message']}")
    
    # Try radio buttons
    print("\n10. Testing radio button focus...")
    try:
        mcq_radio = driver.find_element(By.XPATH, "//input[@type='radio'][@value='mcq']")
        mcq_radio.click()
        time.sleep(0.5)
        
        active_element = driver.switch_to.active_element
        radio_focused = (active_element.get_attribute('value') == 'mcq')
        print(f"  Radio button focused: {radio_focused}")
    except Exception as e:
        print(f"  ❌ Error with radio button: {e}")
    
    print("\n11. Final console logs:")
    logs = driver.get_log('browser')
    if logs:
        for log in logs[-30:]:
            print(f"    [{log['level']}] {log['message']}")
    
    print("\n✅ Test completed. Keeping browser open for 30 seconds for inspection...")
    time.sleep(30)
    
except Exception as e:
    print(f"\n❌ Error during test: {e}")
    import traceback
    traceback.print_exc()
    
    # Print any console logs
    try:
        logs = driver.get_log('browser')
        if logs:
            print("\nBrowser console logs:")
            for log in logs:
                print(f"  [{log['level']}] {log['message']}")
    except:
        pass
    
    time.sleep(10)
finally:
    print("\n🏁 Closing browser...")
    driver.quit()

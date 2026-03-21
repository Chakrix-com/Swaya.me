"""
Capture key authenticated + session screens.
Session 266, join code 457299, quiz 66
"""
import time, os, requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

BASE_URL = "https://test.swaya.me"
OUT_DIR = "/home/vinay/Swaya.me/frontend/public/help"
EMAIL = "demo@swaya.me"
PASSWORD = "Demo1234"
QUIZ_ID = 66
SESSION_ID = 266
JOIN_CODE = "457299"

options = webdriver.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1280,800")

driver = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=options)
wait = WebDriverWait(driver, 15)

def snap(name, delay=2):
    time.sleep(delay)
    p = os.path.join(OUT_DIR, f"{name}.png")
    driver.save_screenshot(p)
    print(f"  ✓ {name}.png  ({os.path.getsize(p)//1024}KB)")

def login():
    driver.get(f"{BASE_URL}/login")
    time.sleep(2)
    inputs = [i for i in driver.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    inputs[0].send_keys(EMAIL)
    [i for i in inputs if i.get_attribute('type') == 'password'][0].send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))
    time.sleep(2)
    print("  ✓ logged in")

try:
    login()

    # === Quiz control / join code screen ===
    print("Quiz session control (join code screen)...")
    driver.get(f"{BASE_URL}/quiz/{QUIZ_ID}/control")
    time.sleep(3)
    snap("quiz_session_joincode", delay=1)

    # Try advancing to first question
    try:
        btns = driver.find_elements(By.XPATH, "//button[contains(., 'Start') or contains(., 'Next') or contains(., 'Begin') or contains(., 'Launch')]")
        for btn in btns:
            if btn.is_displayed() and btn.is_enabled():
                print(f"  Clicking: {btn.text}")
                btn.click()
                time.sleep(2)
                break
        snap("quiz_session_question_active", delay=1)
    except Exception as e:
        print(f"  (advance: {e})")

    # === Audience side — join with code ===
    print("Audience join with pre-filled code...")
    driver.get(f"{BASE_URL}/join/{JOIN_CODE}")
    time.sleep(2)
    snap("audience_join_with_code", delay=1)

    # Enter name and join
    try:
        name_inputs = [i for i in driver.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
        if name_inputs:
            name_inputs[0].send_keys("Alex")
            snap("audience_name_entered", delay=1)
            btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            btn.click()
            time.sleep(3)
            snap("audience_in_session_waiting", delay=1)
    except Exception as e:
        print(f"  (audience join: {e})")

    # === Go back to host — advance question ===
    print("Back to host control to advance...")
    driver.get(f"{BASE_URL}/quiz/{QUIZ_ID}/control")
    time.sleep(2)
    try:
        btns = driver.find_elements(By.XPATH, "//button[contains(., 'Next') or contains(., 'Start Question') or contains(., 'Show')]")
        for btn in btns:
            if btn.is_displayed() and btn.is_enabled():
                print(f"  Clicking: '{btn.text}'")
                btn.click()
                time.sleep(2)
                break
    except Exception as e:
        print(f"  (advance: {e})")
    snap("quiz_session_question_visible", delay=1)

    # === New browser window for audience — see question ===
    # Open a second tab for audience
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(f"{BASE_URL}/join/{JOIN_CODE}")
    time.sleep(2)
    name_inputs = [i for i in driver.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    if name_inputs:
        name_inputs[0].send_keys("Sam")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)
        snap("audience_answering_question", delay=1)
    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    # === Quiz history / results ===
    print("Quiz history...")
    driver.get(f"{BASE_URL}/quiz/{QUIZ_ID}/history")
    time.sleep(3)
    snap("quiz_history_results", delay=1)

    # === Quiz builder — better shot ===
    print("Quiz builder...")
    driver.get(f"{BASE_URL}/quiz/{QUIZ_ID}/edit")
    time.sleep(3)
    snap("quiz_builder", delay=1)

    print("\n=== Done! ===")

except Exception as e:
    import traceback; traceback.print_exc()
    driver.save_screenshot(os.path.join(OUT_DIR, "_error3.png"))
finally:
    driver.quit()

"""
Capture screenshots of key screens on test.swaya.me for the Help Center page.
Saves PNGs to frontend/public/help/
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = "https://test.swaya.me"
OUT_DIR = "/home/vinay/Swaya.me/frontend/public/help"
EMAIL = "demo@swaya.me"
PASSWORD = "Demo1234"

options = webdriver.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1280,800")
# Remove headless so noVNC shows it
# options.add_argument("--headless")

driver = webdriver.Remote(
    command_executor="http://localhost:4444/wd/hub",
    options=options,
)
wait = WebDriverWait(driver, 15)

def snap(name, selector=None, delay=2):
    time.sleep(delay)
    if selector:
        try:
            el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        except TimeoutException:
            pass
    path = os.path.join(OUT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    print(f"  ✓ {name}.png")

def login():
    driver.get(f"{BASE_URL}/login")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[id*='email'], input[name*='email']")))
    time.sleep(1)
    # Find email/username input
    try:
        inp = driver.find_element(By.CSS_SELECTOR, "input[id*='email']")
    except:
        inp = driver.find_elements(By.CSS_SELECTOR, "input")[0]
    inp.clear()
    inp.send_keys(EMAIL)
    try:
        pwd = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    except:
        pwd = driver.find_elements(By.CSS_SELECTOR, "input")[1]
    pwd.clear()
    pwd.send_keys(PASSWORD)
    # Click login button
    btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    btn.click()
    # Wait for dashboard
    wait.until(EC.url_contains("/dashboard"))
    time.sleep(2)
    print("  ✓ Logged in")

try:
    print("=== Public pages ===")

    # 1. Home page
    print("Capturing home page...")
    driver.get(BASE_URL)
    snap("home", delay=2)

    # 2. Audience join page (clean)
    print("Capturing join page...")
    driver.get(f"{BASE_URL}/join")
    snap("audience_join", delay=2)

    print("\n=== Authenticated pages ===")
    login()

    # 3. Dashboard
    print("Capturing dashboard...")
    driver.get(f"{BASE_URL}/dashboard")
    snap("dashboard", ".ant-pro-layout", delay=3)

    # 4. Quiz builder — new quiz
    print("Capturing quiz builder...")
    driver.get(f"{BASE_URL}/quiz/new")
    snap("quiz_builder_new", delay=3)

    # Try to find a quiz to open the builder with
    # First check if there are any quizzes
    driver.get(f"{BASE_URL}/dashboard")
    time.sleep(3)

    # Try clicking "New Quiz" button or find existing quiz
    try:
        new_btn = driver.find_element(By.XPATH, "//*[contains(text(),'New Quiz') or contains(text(),'Create')]")
        new_btn.click()
        time.sleep(2)
        snap("quiz_builder_form", delay=2)
    except:
        pass

    # 5. Quiz builder with a question form open
    driver.get(f"{BASE_URL}/quiz/new")
    time.sleep(3)
    # Try to find and click "Add Question" button
    try:
        add_q = driver.find_element(By.XPATH, "//*[contains(text(),'Add Question') or contains(text(),'question')]")
        add_q.click()
        time.sleep(2)
        snap("quiz_builder_question", delay=1)
    except:
        snap("quiz_builder_empty", delay=1)

    # 6. Try to find the session control for any existing active/ready quiz
    # Navigate to history/results if any
    print("Capturing session control (best effort)...")
    # Get quiz list from API
    import requests
    try:
        r = requests.post(f"{BASE_URL}/api/v1/auth/login",
                          json={"email": EMAIL, "password": PASSWORD})
        token = r.json().get("access_token")
        quizzes = requests.get(f"{BASE_URL}/api/v1/quizzes",
                               headers={"Authorization": f"Bearer {token}"}).json()
        if isinstance(quizzes, list) and len(quizzes) > 0:
            quiz_id = quizzes[0].get("id")
            driver.get(f"{BASE_URL}/quiz/{quiz_id}/edit")
            snap("quiz_builder_existing", delay=3)
    except Exception as e:
        print(f"  (quiz list error: {e})")

    # 7. Results / export page
    print("Capturing results page (best effort)...")
    try:
        if isinstance(quizzes, list) and len(quizzes) > 0:
            quiz_id = quizzes[0].get("id")
            driver.get(f"{BASE_URL}/quiz/{quiz_id}/history")
            snap("quiz_history", delay=3)
    except:
        pass

    print("\n=== Done! ===")
    print(f"Screenshots saved to {OUT_DIR}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    driver.save_screenshot(os.path.join(OUT_DIR, "_error.png"))

finally:
    driver.quit()

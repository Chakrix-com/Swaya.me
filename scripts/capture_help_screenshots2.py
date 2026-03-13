"""
Capture additional targeted screenshots for Help Center.
"""
import time
import os
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = "https://test.swaya.me"
API_URL = "https://test.swaya.me/api/v1"
OUT_DIR = "/home/vinay/Swaya.me/frontend/public/help"
EMAIL = "demo@swaya.me"
PASSWORD = "Demo1234"

options = webdriver.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1280,800")

driver = webdriver.Remote(
    command_executor="http://localhost:4444/wd/hub",
    options=options,
)
wait = WebDriverWait(driver, 15)

def snap(name, delay=2):
    time.sleep(delay)
    path = os.path.join(OUT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    sz = os.path.getsize(path) // 1024
    print(f"  ✓ {name}.png  ({sz}KB)")

def get_token():
    r = requests.post(f"{API_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    return r.json().get("access_token")

def login_browser():
    driver.get(f"{BASE_URL}/login")
    time.sleep(2)
    # Find all visible, enabled inputs
    all_inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']):not([disabled])")
    visible = [i for i in all_inputs if i.is_displayed() and i.is_enabled()]
    print(f"  Visible inputs: {[i.get_attribute('type') or i.get_attribute('name') or i.get_attribute('placeholder') for i in visible]}")
    visible[0].send_keys(EMAIL)
    pwd_inputs = [i for i in visible if i.get_attribute('type') == 'password']
    pwd_inputs[0].send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))
    time.sleep(2)
    print("  ✓ logged in")

try:
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Get or create a quiz with questions
    quizzes = requests.get(f"{API_URL}/quizzes", headers=headers).json()
    print(f"Found {len(quizzes)} quizzes")

    quiz_with_questions = None
    for q in quizzes:
        qid = q["id"]
        detail = requests.get(f"{API_URL}/quizzes/{qid}", headers=headers).json()
        if detail.get("questions") and len(detail["questions"]) > 0:
            quiz_with_questions = detail
            print(f"  Using quiz {qid}: '{q.get('title')}' with {len(detail['questions'])} questions")
            break

    if not quiz_with_questions:
        print("No quiz with questions found, using first quiz")
        if quizzes:
            quiz_with_questions = requests.get(f"{API_URL}/quizzes/{quizzes[0]['id']}", headers=headers).json()

    login_browser()

    # === Dashboard — good overview ===
    print("Dashboard...")
    driver.get(f"{BASE_URL}/dashboard")
    snap("dashboard", delay=3)

    if quiz_with_questions:
        qid = quiz_with_questions["id"]

        # === Quiz builder / editor ===
        print("Quiz builder (edit existing)...")
        driver.get(f"{BASE_URL}/quiz/{qid}/edit")
        time.sleep(3)
        snap("quiz_builder_with_questions", delay=1)

        # Try clicking the first question to expand/edit it
        try:
            q_items = driver.find_elements(By.CSS_SELECTOR, ".ant-collapse-header, .ant-list-item, [class*='question']")
            if q_items:
                q_items[0].click()
                time.sleep(1)
                snap("quiz_builder_question_open", delay=1)
        except: pass

        # Try clicking "Add Question" button
        try:
            btns = driver.find_elements(By.XPATH, "//*[contains(text(),'Add Question') or contains(text(),'Add question') or contains(text(),'+ Question')]")
            if btns:
                btns[0].click()
                time.sleep(2)
                snap("quiz_builder_add_question", delay=1)
                # Press Escape to close
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(1)
        except Exception as e:
            print(f"  (add question btn: {e})")

        # === Session control / join code ===
        # Check if there's an active session or start one
        sessions = requests.get(f"{API_URL}/quizzes/{qid}/sessions", headers=headers).json()
        print(f"  Sessions: {[s.get('status') for s in sessions] if isinstance(sessions, list) else sessions}")

        active_session = None
        if isinstance(sessions, list):
            for s in sessions:
                if s.get("status") in ("CREATED", "ACTIVE"):
                    active_session = s
                    break

        if not active_session:
            print("  Starting a new session...")
            try:
                resp = requests.post(f"{API_URL}/quizzes/{qid}/sessions", headers=headers).json()
                print(f"  Created session: {resp.get('id')}, status: {resp.get('status')}")
                active_session = resp
            except Exception as e:
                print(f"  (session start error: {e})")

        if active_session:
            sid = active_session["id"]
            print(f"Quiz control for session {sid}...")
            driver.get(f"{BASE_URL}/quiz/{qid}/control")
            time.sleep(3)
            snap("quiz_session_control", delay=2)

            # Try to advance to first question
            try:
                start_btns = driver.find_elements(By.XPATH, "//*[contains(text(),'Start') or contains(text(),'Next') or contains(text(),'Begin')]")
                if start_btns:
                    for btn in start_btns:
                        try:
                            btn.click()
                            time.sleep(1)
                            break
                        except: pass
                snap("quiz_session_question_live", delay=2)
            except: pass

            # History page
            print("Quiz history/results page...")
            driver.get(f"{BASE_URL}/quiz/{qid}/history")
            snap("quiz_history", delay=3)

    # === Audience join — clean ===
    print("Audience join page...")
    driver.get(f"{BASE_URL}/join")
    snap("audience_join", delay=2)

    # If there's a session with a join code, show it pre-filled
    if quiz_with_questions and active_session:
        join_code = active_session.get("join_code")
        # Also check the quiz event
        if not join_code:
            ev = requests.get(f"{API_URL}/quizzes/{quiz_with_questions['id']}", headers=headers).json()
            join_code = ev.get("join_code") or ev.get("event", {}).get("join_code")
        if join_code:
            print(f"  Join code: {join_code}")
            driver.get(f"{BASE_URL}/join/{join_code}")
            snap("audience_join_with_code", delay=2)
            # Try entering a name
            try:
                name_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='name' i], input[placeholder*='Name' i]")
                name_input.send_keys("Test User")
                snap("audience_join_name_entered", delay=1)
                # Submit
                btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                btn.click()
                time.sleep(3)
                snap("audience_in_session", delay=2)
            except Exception as e:
                print(f"  (name entry: {e})")

    print("\n=== Done! ===")

except Exception as e:
    import traceback; traceback.print_exc()
    driver.save_screenshot(os.path.join(OUT_DIR, "_error2.png"))
finally:
    driver.quit()

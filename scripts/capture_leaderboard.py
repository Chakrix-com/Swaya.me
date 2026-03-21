"""
Capture leaderboard screenshots.
Creates a fresh quiz session, simulates 3 participants answering,
then screenshots the leaderboard from both host and audience views.
"""
import time, os, requests, json, threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://test.swaya.me"
API = "https://test.swaya.me/api/v1"
OUT = "/home/vinay/Swaya.me/frontend/public/assets/help-screens"
EMAIL = "demo@swaya.me"
PASSWORD = "Demo1234"

def get_token():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    return r.json()["access_token"]

def make_driver(w=1280, h=900):
    opts = webdriver.ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(f"--window-size={w},{h}")
    return webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=opts)

def snap(driver, name, delay=2):
    time.sleep(delay)
    p = os.path.join(OUT, f"{name}.png")
    driver.save_screenshot(p)
    print(f"  ✓ {name}.png ({os.path.getsize(p)//1024}KB)")

token = get_token()
h = {"Authorization": f"Bearer {token}"}

# Find a quiz with MCQ questions in READY state
quizzes = requests.get(f"{API}/quizzes", headers=h).json()
quiz = None
for q in quizzes:
    if q.get("status") == "ready":
        detail = requests.get(f"{API}/quizzes/{q['id']}", headers=h).json()
        mcqs = [qq for qq in detail.get("questions", []) if qq.get("question_type") == "mcq"]
        if mcqs:
            quiz = detail
            quiz["mcq_questions"] = mcqs
            print(f"Using quiz {q['id']}: '{q['title']}' — {len(mcqs)} MCQ question(s)")
            break

if not quiz:
    print("No suitable quiz found"); exit(1)

quiz_id = quiz["id"]

# Start fresh session
resp = requests.post(f"{API}/quizzes/sessions/start?quiz_id={quiz_id}", headers=h)
session = resp.json()
session_id = session["id"]
join_code = session["join_code"]
print(f"Session {session_id}, join code: {join_code}")

# ── Host driver ────────────────────────────────────────────────────────────────
host = make_driver()
wait_h = WebDriverWait(host, 15)

def login_host():
    host.get(f"{BASE_URL}/login")
    time.sleep(2)
    inputs = [i for i in host.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    inputs[0].send_keys(EMAIL)
    [i for i in inputs if i.get_attribute("type") == "password"][0].send_keys(PASSWORD)
    host.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait_h.until(EC.url_contains("/dashboard"))
    time.sleep(2)
    print("  ✓ host logged in")

def audience_flow(name, answer_index, delay_before_answer=1):
    """Each participant in their own thread."""
    d = make_driver(1024, 768)
    try:
        d.get(f"{BASE_URL}/join/{join_code}")
        time.sleep(2)
        name_inputs = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
        if name_inputs:
            name_inputs[0].send_keys(name)
            d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            time.sleep(3)
            print(f"  ✓ {name} joined")
            # Wait for question to appear
            for _ in range(20):
                btns = [b for b in d.find_elements(By.CSS_SELECTOR, "button, .ant-radio-button-wrapper") if b.is_displayed()]
                option_btns = [b for b in btns if b.text.strip() and b.text not in ("Leave", "Submit", "")]
                if len(option_btns) >= 2:
                    break
                time.sleep(1)
            time.sleep(delay_before_answer)
            # Click option
            option_btns = [b for b in d.find_elements(By.CSS_SELECTOR, ".ant-btn, .ant-radio-button-wrapper")
                          if b.is_displayed() and b.text.strip() and b.text not in ("Leave",)]
            if len(option_btns) > answer_index:
                option_btns[answer_index].click()
                print(f"  ✓ {name} answered option {answer_index}")
            time.sleep(2)
    except Exception as e:
        print(f"  ({name} error: {e})")
    finally:
        d.quit()

try:
    login_host()

    # Go to quiz control
    host.get(f"{BASE_URL}/quiz/{quiz_id}/control")
    time.sleep(3)
    snap(host, "quiz_session_joincode", delay=1)

    # Start first question
    btns = [b for b in host.find_elements(By.XPATH, "//button[contains(., 'Start Session') or contains(., 'Start Question') or contains(., 'Begin')]") if b.is_displayed() and b.is_enabled()]
    if btns:
        btns[0].click()
        print(f"  Clicked: {btns[0].text}")
        time.sleep(2)

    snap(host, "quiz_session_question_active", delay=1)

    # Launch 3 audience participants in parallel threads
    t1 = threading.Thread(target=audience_flow, args=("Alice", 0, 0.5))   # fast, correct (index 0 = A)
    t2 = threading.Thread(target=audience_flow, args=("Bob",   0, 2.0))   # slower, correct
    t3 = threading.Thread(target=audience_flow, args=("Carol", 1, 1.0))   # wrong answer
    t1.start(); t2.start(); t3.start()
    t1.join(); t2.join(); t3.join()

    time.sleep(2)

    # Close question to lock in answers
    try:
        close_btns = [b for b in host.find_elements(By.XPATH, "//button[contains(., 'Close') or contains(., 'End Question') or contains(., 'Next')]") if b.is_displayed() and b.is_enabled()]
        if close_btns:
            close_btns[0].click()
            print(f"  Clicked: {close_btns[0].text}")
            time.sleep(2)
    except: pass

    snap(host, "quiz_leaderboard_host", delay=2)

    # End session
    try:
        end_btns = [b for b in host.find_elements(By.XPATH, "//button[contains(., 'End Session') or contains(., 'Finish')]") if b.is_displayed() and b.is_enabled()]
        if end_btns:
            end_btns[0].click()
            time.sleep(2)
            # Confirm if modal appears
            confirm_btns = [b for b in host.find_elements(By.XPATH, "//button[contains(., 'OK') or contains(., 'Confirm') or contains(., 'Yes')]") if b.is_displayed()]
            if confirm_btns:
                confirm_btns[0].click()
                time.sleep(2)
    except: pass

    # History/results page
    host.get(f"{BASE_URL}/quiz/{quiz_id}/history")
    time.sleep(3)
    snap(host, "quiz_history_results", delay=1)

    print("\nDone!")

except Exception as e:
    import traceback; traceback.print_exc()
    host.save_screenshot(os.path.join(OUT, "_error_lb.png"))
finally:
    host.quit()

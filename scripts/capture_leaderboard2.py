"""
Capture leaderboard screenshot.
Simulates participants via API, screenshots leaderboard with single browser session.
"""
import time, os, requests
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

token = get_token()
h = {"Authorization": f"Bearer {token}"}

# Find quiz 66 "Another Test" (ready, MCQ)
quiz_id = 39
detail = requests.get(f"{API}/quizzes/{quiz_id}", headers=h).json()
mcqs = [q for q in detail.get("questions", []) if q.get("question_type") == "mcq"]
print(f"Quiz {quiz_id}: '{detail.get('title')}', {len(mcqs)} MCQ question(s)")
if not mcqs:
    print("No MCQ questions"); exit(1)

question = mcqs[0]
correct_idx = question.get("correct_answer_index", 0)
wrong_idx = (correct_idx + 1) % 4
print(f"Question: '{question['text']}', correct option index: {correct_idx}")

# Start fresh session
resp = requests.post(f"{API}/quizzes/sessions/start?quiz_id={quiz_id}", headers=h)
session = resp.json()
session_id = session["id"]
join_code = session["join_code"]
print(f"Session {session_id}, join code: {join_code}")

def join_participant(name):
    r = requests.post(f"{API}/quizzes/sessions/join", json={"join_code": join_code, "display_name": name})
    data = r.json()
    return data.get("session_token"), data.get("session_id")

def submit_answer(session_token, question_id, answer_index, sid):
    r = requests.post(
        f"{API}/quizzes/sessions/submit-answer",
        params={"session_token": session_token},
        json={
            "session_id": sid,
            "question_id": question_id,
            "selected_option_index": answer_index,
        }
    )
    return r.status_code, r.json()

# Join participants
print("Joining participants via API...")
alice_token, _ = join_participant("Alice")
bob_token, _ = join_participant("Bob")
carol_token, _ = join_participant("Carol")
print(f"  Alice: {alice_token[:20] if alice_token else 'FAILED'}...")
print(f"  Bob: {bob_token[:20] if bob_token else 'FAILED'}...")
print(f"  Carol: {carol_token[:20] if carol_token else 'FAILED'}...")

# ── Browser: host control ─────────────────────────────────────────────────────
opts = webdriver.ChromeOptions()
opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1280,900")
driver = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=opts)
wait = WebDriverWait(driver, 15)

def snap(name, delay=2):
    time.sleep(delay)
    p = os.path.join(OUT, f"{name}.png")
    driver.save_screenshot(p)
    print(f"  ✓ {name}.png ({os.path.getsize(p)//1024}KB)")

try:
    # Login
    driver.get(f"{BASE_URL}/login")
    time.sleep(2)
    inputs = [i for i in driver.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    inputs[0].send_keys(EMAIL)
    [i for i in inputs if i.get_attribute("type") == "password"][0].send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))
    time.sleep(2)
    print("  ✓ logged in")

    # Go to control page
    driver.get(f"{BASE_URL}/quiz/{quiz_id}/control")
    time.sleep(3)
    snap("quiz_session_joincode", delay=1)

    # Start the session (click Start Session)
    btns = [b for b in driver.find_elements(By.XPATH, "//button") if "Start Session" in b.text and b.is_displayed()]
    if btns:
        btns[0].click()
        print("  Clicked: Start Session")
        time.sleep(2)

    # Start question 1
    time.sleep(1)
    all_btns = driver.find_elements(By.XPATH, "//button")
    visible = [b for b in all_btns if b.is_displayed() and b.is_enabled() and b.text.strip()]
    for b in visible[:8]:
        print(f"  Btn: '{b.text}'")
    q_btns = [b for b in visible if any(x in b.text for x in ["Start Question", "Start First", "Next Question", "Begin", "Show Q"])]
    if q_btns:
        q_btns[0].click()
        print(f"  Clicked: {q_btns[0].text}")
        time.sleep(2)

    snap("quiz_session_question_active", delay=1)

    # Submit answers via API (staggered so Alice is faster)
    q_id = question["id"]
    print(f"Submitting answers via API (question id={q_id})...")
    time.sleep(0.2)
    s, r = submit_answer(alice_token, q_id, correct_idx, session_id)
    print(f"  Alice (correct, fast): {s} - {r}")
    time.sleep(1.5)
    s, r = submit_answer(carol_token, q_id, wrong_idx, session_id)
    print(f"  Carol (wrong): {s} - {r}")
    time.sleep(0.5)
    s, r = submit_answer(bob_token, q_id, correct_idx, session_id)
    print(f"  Bob (correct, slow): {s} - {r}")

    time.sleep(2)

    # Close question
    btns = [b for b in driver.find_elements(By.XPATH, "//button") if b.is_displayed() and b.is_enabled() and any(x in b.text for x in ["Close Question", "Next Question", "Close", "Next"])]
    if btns:
        btns[0].click()
        print(f"  Closed question: {btns[0].text}")
        time.sleep(2)

    # Screenshot with leaderboard visible
    snap("quiz_leaderboard_host", delay=2)

    # Scroll down to see leaderboard if needed
    driver.execute_script("window.scrollBy(0, 400)")
    time.sleep(1)
    snap("quiz_leaderboard_host_scrolled", delay=1)

    # End session
    btns = [b for b in driver.find_elements(By.XPATH, "//button") if b.is_displayed() and b.is_enabled() and "End Session" in b.text]
    if btns:
        btns[0].click()
        time.sleep(1)
        confirm = [b for b in driver.find_elements(By.XPATH, "//button") if b.is_displayed() and any(x in b.text for x in ["OK", "Yes", "Confirm"])]
        if confirm:
            confirm[0].click()
            time.sleep(2)

    driver.get(f"{BASE_URL}/quiz/{quiz_id}/history")
    time.sleep(3)
    snap("quiz_history_results", delay=1)

    print("\nDone!")

except Exception as e:
    import traceback; traceback.print_exc()
    try: driver.save_screenshot(os.path.join(OUT, "_error_lb2.png"))
    except: pass
finally:
    driver.quit()

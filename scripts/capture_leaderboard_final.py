"""
Capture a clean, focused leaderboard screenshot for the Help page.
Session 269, join code 043453, quiz 39.
4 unique participants, answers submitted fast, screenshot framed on just the leaderboard table.
"""
import time, os, requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

API  = "https://test.swaya.me/api/v1"
BASE = "https://test.swaya.me"
OUT  = "/home/vinay/Swaya.me/frontend/public/assets/help-screens"

SESSION_ID = 269
JOIN_CODE  = "043453"
QUIZ_ID    = 39

token = requests.post(f"{API}/auth/login", json={"email": "demo@swaya.me", "password": "Demo1234"}).json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

# Q1: "What is the capital of France?" correct=1 (Paris)
detail = requests.get(f"{API}/quizzes/{QUIZ_ID}", headers=h).json()
q1 = [q for q in detail["questions"] if q["question_type"] == "mcq"][0]
correct, wrong = q1["correct_answer_index"], (q1["correct_answer_index"] + 1) % 4
print(f"Q1 id={q1['id']} correct={correct} ({q1['options'][correct]})")

# Join 4 unique participants
def join(name):
    r = requests.post(f"{API}/quizzes/sessions/join", json={"join_code": JOIN_CODE, "display_name": name})
    return r.json().get("session_token")

t = {name: join(name) for name in ["Priya", "James", "Sofia", "Ravi"]}
print("Joined:", {k: bool(v) for k, v in t.items()})

opts = webdriver.ChromeOptions()
opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1280,860")
d = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=opts)
wait = WebDriverWait(d, 15)

def snap(name, delay=1):
    time.sleep(delay)
    p = os.path.join(OUT, f"{name}.png")
    d.save_screenshot(p)
    print(f"  ✓ {name}.png ({os.path.getsize(p)//1024}KB)")

def click(texts, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for b in d.find_elements(By.XPATH, "//button"):
            if b.is_displayed() and b.is_enabled() and any(x in b.text for x in texts):
                print(f"  → '{b.text.strip()[:50]}'")
                b.click()
                return True
        time.sleep(0.5)
    print(f"  (not found: {texts})")
    return False

def submit(tok, idx):
    return requests.post(
        f"{API}/quizzes/sessions/submit-answer",
        params={"session_token": tok},
        json={"session_id": SESSION_ID, "question_id": q1["id"], "selected_option_index": idx},
    ).json()

try:
    # Login
    d.get(f"{BASE}/login")
    time.sleep(2)
    inputs = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    inputs[0].send_keys("demo@swaya.me")
    [i for i in inputs if i.get_attribute("type") == "password"][0].send_keys("Demo1234")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))
    time.sleep(2)

    d.get(f"{BASE}/quiz/{QUIZ_ID}/control")
    time.sleep(3)

    # Start session → start Q1
    click(["Start Session"])
    time.sleep(1)
    click(["Start First Question", "Start Question"])
    time.sleep(1.5)  # question is now OPEN

    # Submit answers fast — realistic gaps (1–4 seconds apart)
    r = submit(t["Priya"], correct); print(f"  Priya  correct: {r.get('success')}")
    time.sleep(1.4)
    r = submit(t["James"], correct); print(f"  James  correct: {r.get('success')}")
    time.sleep(0.9)
    r = submit(t["Ravi"],  wrong);   print(f"  Ravi   wrong:   {r.get('success')}")
    time.sleep(0.6)
    r = submit(t["Sofia"], wrong);   print(f"  Sofia  wrong:   {r.get('success')}")
    time.sleep(1)

    # Close question (lock answers, don't advance to Q2)
    click(["Close Question", "End Question", "Lock Answers"])
    time.sleep(3)  # leaderboard loads

    # Scroll the leaderboard heading into view, then nudge down a little
    # so the table header is near the top of the viewport
    try:
        lb = d.find_element(By.XPATH, "//*[contains(@class,'ant-table') or contains(text(),'Leaderboard')]")
        d.execute_script("arguments[0].scrollIntoView({block:'start'})", lb)
        time.sleep(0.5)
        # Scroll back up slightly so the "Leaderboard" heading is visible
        d.execute_script("window.scrollBy(0, -80)")
        time.sleep(0.5)
    except Exception as e:
        print(f"  (scroll: {e})")
        d.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.55)")
        time.sleep(0.5)

    snap("quiz_leaderboard_host", delay=1)

    print("Done!")

except Exception as e:
    import traceback; traceback.print_exc()
    try: d.save_screenshot(os.path.join(OUT, "_err_final.png"))
    except: pass
finally:
    d.quit()

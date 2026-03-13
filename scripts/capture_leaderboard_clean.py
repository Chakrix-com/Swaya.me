"""
Capture a clean leaderboard screenshot.
Flow: start session → participants answer Q1 via API → close question → scroll to leaderboard → screenshot.
"""
import time, os, requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

API = "https://test.swaya.me/api/v1"
BASE = "https://test.swaya.me"
OUT = "/home/vinay/Swaya.me/frontend/public/assets/help-screens"

token = requests.post(f"{API}/auth/login", json={"email": "demo@swaya.me", "password": "Demo1234"}).json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

# Quiz 39: 5 MCQ questions, Q1 = "What is the capital of France?" correct=1 (Paris)
quiz_id = 39
detail = requests.get(f"{API}/quizzes/{quiz_id}", headers=h).json()
q1 = [q for q in detail["questions"] if q["question_type"] == "mcq"][0]
correct = q1["correct_answer_index"]   # 1
wrong   = (correct + 1) % 4           # 2
print(f"Q1: '{q1['text']}' — correct={correct} ({q1['options'][correct]})")

# Start fresh session
sess = requests.post(f"{API}/quizzes/sessions/start?quiz_id={quiz_id}", headers=h).json()
session_id = sess["id"]
join_code  = sess["join_code"]
print(f"Session {session_id}, code: {join_code}")

# Join 4 participants
def join(name):
    r = requests.post(f"{API}/quizzes/sessions/join", json={"join_code": join_code, "display_name": name})
    return r.json().get("session_token")

def answer(token, option_idx):
    return requests.post(
        f"{API}/quizzes/sessions/submit-answer",
        params={"session_token": token},
        json={"session_id": session_id, "question_id": q1["id"], "selected_option_index": option_idx},
    ).json()

t_alice = join("Alice")
t_bob   = join("Bob")
t_carol = join("Carol")
t_dave  = join("Dave")
print(f"Joined: Alice={bool(t_alice)} Bob={bool(t_bob)} Carol={bool(t_carol)} Dave={bool(t_dave)}")

# ── Browser ───────────────────────────────────────────────────────────────────
opts = webdriver.ChromeOptions()
opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1400,900")
d = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=opts)
wait = WebDriverWait(d, 15)

def snap(name, delay=1):
    time.sleep(delay)
    p = os.path.join(OUT, f"{name}.png")
    d.save_screenshot(p)
    print(f"  ✓ {name}.png ({os.path.getsize(p)//1024}KB)")

def click_button_containing(texts, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for b in d.find_elements(By.XPATH, "//button"):
            if b.is_displayed() and b.is_enabled() and any(t in b.text for t in texts):
                print(f"  Clicking: '{b.text.strip()[:40]}'")
                b.click()
                return True
        time.sleep(0.5)
    return False

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

    # Quiz control
    d.get(f"{BASE}/quiz/{quiz_id}/control")
    time.sleep(3)

    # Start session
    click_button_containing(["Start Session"])
    time.sleep(2)

    # Start first question
    click_button_containing(["Start First Question", "Start Question"])
    time.sleep(2)
    snap("quiz_session_question_active")

    # Submit answers via API with time gaps (Alice fastest → rank 1, Bob slower → rank 2, Carol/Dave wrong → rank 3/4)
    print("Submitting answers...")
    time.sleep(0.3);  r = answer(t_alice, correct); print(f"  Alice (correct, fast): {r.get('success')}")
    time.sleep(1.2);  r = answer(t_dave,  wrong);   print(f"  Dave  (wrong):         {r.get('success')}")
    time.sleep(0.8);  r = answer(t_carol, wrong);   print(f"  Carol (wrong):         {r.get('success')}")
    time.sleep(1.0);  r = answer(t_bob,   correct); print(f"  Bob   (correct, slow): {r.get('success')}")
    time.sleep(1)

    # Close question (do NOT advance — just close so leaderboard updates)
    click_button_containing(["Close Question", "End Question", "Lock Answers"])
    time.sleep(3)  # give leaderboard time to load

    # Scroll to leaderboard element
    try:
        lb_el = d.find_element(By.XPATH, "//*[contains(text(),'Leaderboard') or contains(text(),'leaderboard') or contains(text(),'Rank')]")
        d.execute_script("arguments[0].scrollIntoView({behavior:'smooth', block:'center'})", lb_el)
        time.sleep(1)
        print(f"  Scrolled to leaderboard element: '{lb_el.text[:40]}'")
    except Exception as e:
        print(f"  (scroll to leaderboard: {e}) — scrolling down 500px instead")
        d.execute_script("window.scrollBy(0, 500)")
        time.sleep(1)

    snap("quiz_leaderboard_host", delay=1)

    # Also try scrolling a bit more to show the full table
    d.execute_script("window.scrollBy(0, 150)")
    snap("quiz_leaderboard_host_full", delay=1)

    print("\nDone! Check screenshots in OUT folder.")

except Exception as e:
    import traceback; traceback.print_exc()
    try: d.save_screenshot(os.path.join(OUT, "_error_lb_clean.png"))
    except: pass
finally:
    d.quit()

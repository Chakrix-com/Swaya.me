"""
Selenium test: verify leaderboard shows time for wrong AND right answers.

Scenario:
  - Host starts quiz 11 (5 MCQ questions)
  - Participant "Alice" joins and answers Q1 WRONG
  - Leaderboard checked → time must be non-null
  - Host advances to Q2
  - Participant "Alice" answers Q2 RIGHT
  - Leaderboard checked → cumulative time shown
"""

import time, requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://www.swaya.me"
API  = f"{BASE}/api/v1"
QUIZ_ID = 11          # Demo Quiz – General Knowledge (5 MCQ Qs)
HOST_EMAIL    = "demo@swaya.me"
HOST_PASSWORD = "Demo1234"

# Q15: correct=1 (Paris). We'll answer index 0 (London) → WRONG
Q1_ID      = 15
Q1_WRONG   = 0   # London
Q1_CORRECT = 1   # Paris

# Q16: correct=2 (Au). We'll answer index 2 → RIGHT
Q2_ID      = 16
Q2_CORRECT = 2   # Au

WAIT = 10  # seconds

def log(msg):
    print(f"  ► {msg}")

# ── 1. Host login via API ────────────────────────────────────────────────────
log("Logging in as host via API...")
r = requests.post(f"{API}/auth/login",
                  json={"email": HOST_EMAIL, "password": HOST_PASSWORD}, verify=False)
r.raise_for_status()
host_token = r.json()["access_token"]
host_headers = {"Authorization": f"Bearer {host_token}"}
log(f"Host token obtained.")

# ── 2. End any existing active session for quiz 11 only ─────────────────────
log("Checking for existing active sessions on quiz 11...")
r = requests.get(f"{API}/quizzes/{QUIZ_ID}/sessions", headers=host_headers, verify=False)
sessions = r.json().get("sessions", [])
for s in sessions:
    if s["status"] in ("active", "created"):
        log(f"Ending existing session {s['id']}...")
        requests.post(f"{API}/quizzes/sessions/{s['id']}/end", headers=host_headers, verify=False)
        time.sleep(0.5)

# ── 3. Start new session ─────────────────────────────────────────────────────
log("Starting new session...")
r = requests.post(f"{API}/quizzes/sessions/start",
                  params={"quiz_id": QUIZ_ID}, headers=host_headers, verify=False)
r.raise_for_status()
session = r.json()
session_id = session["id"]
join_code   = session["join_code"]
log(f"Session {session_id} started, join code: {join_code}")

# ── 4. Launch Selenium → open QuizPresent as host ────────────────────────────
log("Connecting to Selenium container...")
options = webdriver.ChromeOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--window-size=1400,900")
driver = webdriver.Remote(
    command_executor="http://localhost:4444/wd/hub",
    options=options
)
wait = WebDriverWait(driver, WAIT)

log("Opening QuizPresent page...")
# Inject the host token into localStorage then navigate
driver.get(BASE)
time.sleep(2)
driver.execute_script(
    f"localStorage.setItem('token', '{host_token}');"
)
present_url = f"{BASE}/quiz/session/{session_id}?code={join_code}"
driver.get(present_url)
time.sleep(3)
log("QuizPresent loaded.")

# ── 5. Participant Alice joins via API ───────────────────────────────────────
log("Participant Alice joining...")
r = requests.post(f"{API}/quizzes/sessions/join",
                  json={"join_code": join_code, "display_name": "Alice"}, verify=False)
r.raise_for_status()
alice = r.json()
alice_token = alice["session_token"]
log(f"Alice joined, token: {alice_token[:12]}...")

# ── 6. Host advances to Q1 ───────────────────────────────────────────────────
log("Host advancing to Q1...")
r = requests.post(f"{API}/quizzes/sessions/{session_id}/advance",
                  headers=host_headers, verify=False)
r.raise_for_status()
time.sleep(2)

# ── 7. Alice answers Q1 WRONG ───────────────────────────────────────────────
log(f"Alice answering Q1 WRONG (option {Q1_WRONG})...")
time.sleep(3)  # simulate real response delay
r = requests.post(f"{API}/quizzes/sessions/submit-answer",
                  params={"session_token": alice_token},
                  json={"question_id": Q1_ID, "selected_option_index": Q1_WRONG},
                  verify=False)
log(f"Answer response: {r.status_code} {r.json()}")

# ── 8. Check leaderboard: Alice's time must be non-null ─────────────────────
time.sleep(1)
log("Checking leaderboard after Q1 wrong answer...")
r = requests.get(f"{API}/quizzes/sessions/{session_id}/leaderboard",
                 headers=host_headers, verify=False)
log(f"Leaderboard HTTP status: {r.status_code}")
if not r.text:
    log(f"ERROR: empty response body!")
    driver.quit()
    raise SystemExit(1)
lb = r.json()
entries = lb.get("entries", [])
log(f"Leaderboard entries: {entries}")
assert entries, "No entries in leaderboard!"
alice_entry = next((e for e in entries if e["display_name"] == "Alice"), None)
assert alice_entry, "Alice not found in leaderboard!"
time_after_wrong = alice_entry["time_taken_seconds"]
log(f"Alice time after WRONG answer: {time_after_wrong}")
assert time_after_wrong is not None, \
    f"FAIL: time_taken_seconds is null after wrong answer!"
log(f"PASS: time shows {time_after_wrong}s after wrong answer on Q1.")

# Open leaderboard modal visually
driver.execute_script("window.scrollTo(0,0)")
time.sleep(1)
# Click the leaderboard expand button in sidebar if visible
try:
    lb_btn = driver.find_element(By.CSS_SELECTOR, ".pv-clb-expand-icon")
    lb_btn.click()
    time.sleep(2)
    log("Leaderboard modal opened visually.")
except Exception as e:
    log(f"Could not click leaderboard button: {e}")

time.sleep(3)  # pause for visual inspection

# ── 9. Host advances to Q2 ───────────────────────────────────────────────────
log("Host advancing to Q2 (reveals Q1 answer, then advances)...")
# First advance = reveal
r = requests.post(f"{API}/quizzes/sessions/{session_id}/advance",
                  headers=host_headers, verify=False)
r.raise_for_status()
time.sleep(2)

# ── 10. Alice answers Q2 RIGHT ──────────────────────────────────────────────
log(f"Alice answering Q2 RIGHT (option {Q2_CORRECT})...")
time.sleep(2)
r = requests.post(f"{API}/quizzes/sessions/submit-answer",
                  params={"session_token": alice_token},
                  json={"question_id": Q2_ID, "selected_option_index": Q2_CORRECT},
                  verify=False)
log(f"Answer response: {r.status_code} {r.json()}")

# ── 11. Check leaderboard again: cumulative time, score=1 ───────────────────
time.sleep(1)
log("Checking leaderboard after Q2 right answer...")
r = requests.get(f"{API}/quizzes/sessions/{session_id}/leaderboard",
                 headers=host_headers, verify=False)
lb = r.json()
entries = lb.get("entries", [])
alice_entry = next((e for e in entries if e["display_name"] == "Alice"), None)
time_after_right = alice_entry["time_taken_seconds"]
score_after_right = alice_entry["score"]
log(f"Alice after Q2: score={score_after_right}, time={time_after_right}s")
assert time_after_right is not None, "FAIL: time null after right answer!"
assert score_after_right == 1, f"FAIL: expected score=1 got {score_after_right}"
assert time_after_right >= time_after_wrong, \
    "FAIL: cumulative time should be >= Q1 time"
log(f"PASS: score={score_after_right}, cumulative time={time_after_right}s")

time.sleep(4)  # hold for visual inspection

# ── 12. End session ──────────────────────────────────────────────────────────
log("Ending session...")
requests.post(f"{API}/quizzes/sessions/{session_id}/end",
              headers=host_headers, verify=False)
log("Session ended.")

time.sleep(3)
driver.quit()

print("\n✅  All assertions passed — leaderboard timing works correctly for wrong and right answers.")

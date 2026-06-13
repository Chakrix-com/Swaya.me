"""Fable review pass 2: builder, live session host+participant, exam, offline poll, themes.
Single browser session (container allows 1), multiple windows. test.swaya.me only.
"""
import time, os, json, requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://test.swaya.me"
API = f"{BASE}/api/v1"
OUT = "/tmp/fable-review"
QUIZ_ID = 11
EXAM_URL = f"{BASE}/e/pdftest001"
POLL_URL = f"{BASE}/poll/-y8QIcWpCIg"

tok = requests.post(f"{API}/auth/login", json={"email": "demo@swaya.me", "password": "Demo1234"}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

o = webdriver.ChromeOptions()
o.add_argument("--no-sandbox"); o.add_argument("--disable-dev-shm-usage")
o.add_argument("--window-size=1440,900")
d = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=o)
wait = WebDriverWait(d, 15)

def snap(name, delay=1.5):
    time.sleep(delay)
    d.save_screenshot(os.path.join(OUT, f"{name}.png"))
    print(f"  snap {name}.png url={d.current_url}")

def dump(name):
    open(os.path.join(OUT, f"{name}.txt"), "w").write(d.execute_script("return document.body.innerText"))

session_id = None
try:
    # login (main window = HOST)
    d.get(f"{BASE}/login"); time.sleep(2)
    ins = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    ins[0].send_keys("demo@swaya.me")
    [i for i in ins if i.get_attribute("type") == "password"][0].send_keys("Demo1234")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard")); time.sleep(2)
    HOST = d.current_window_handle

    # participant + present windows
    d.switch_to.new_window('window'); PART = d.current_window_handle
    d.set_window_size(430, 880)
    d.switch_to.new_window('window'); PRES = d.current_window_handle
    d.set_window_size(1440, 900)

    def w(handle): d.switch_to.window(handle); time.sleep(0.3)

    # --- builder
    w(HOST)
    d.get(f"{BASE}/quiz/{QUIZ_ID}/edit")
    snap("10-builder-edit", 4); dump("10-builder-edit")
    edits = [b for b in d.find_elements(By.CSS_SELECTOR, "button") if b.is_displayed() and "edit" in ((b.get_attribute("aria-label") or '') + ' ' + (b.text or '')).lower()]
    if edits:
        edits[0].click(); snap("11-builder-question-editor", 2); dump("11-builder-question-editor")
        d.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE); time.sleep(1)

    # --- history
    d.get(f"{BASE}/quiz/{QUIZ_ID}/history")
    snap("12-history", 3); dump("12-history")

    # --- start live session
    s = requests.post(f"{API}/quizzes/sessions/start", params={"quiz_id": QUIZ_ID}, headers=H).json()
    print("session:", json.dumps(s)[:300])
    session_id = s.get("id") or s.get("session_id")
    join_code = s.get("join_code")
    d.get(f"{BASE}/quiz/{QUIZ_ID}/control")
    snap("13-control-lobby", 4); dump("13-control-lobby")

    # --- participant joins
    w(PART)
    d.get(f"{BASE}/join"); time.sleep(2)
    ins = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed()]
    ins[0].send_keys(str(join_code))
    if len(ins) > 1: ins[1].send_keys("Fable Reviewer")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    snap("14-participant-lobby", 4); dump("14-participant-lobby")
    w(HOST); snap("15-control-with-participant", 2)

    # --- advance to Q1
    requests.post(f"{API}/quizzes/sessions/{session_id}/advance", headers=H)
    snap("16-control-q1", 3); dump("16-control-q1")
    w(PART); snap("17-participant-q1", 2); dump("17-participant-q1")

    opts = [e for e in d.find_elements(By.CSS_SELECTOR, "button, .ant-radio-wrapper, [class*='option']") if e.is_displayed() and (e.text or '').strip()]
    print("participant options:", [x.text[:30] for x in opts[:8]])
    if opts:
        opts[0].click(); time.sleep(1)
        subs = [b for b in d.find_elements(By.CSS_SELECTOR, "button") if b.is_displayed() and "submit" in b.text.lower()]
        if subs: subs[0].click()
    snap("18-participant-answered", 2); dump("18-participant-answered")
    w(HOST); snap("19-control-q1-after-answer", 1)

    # --- present view
    w(PRES)
    d.get(f"{BASE}/present/{session_id}")
    snap("20-present-view", 4); dump("20-present-view")

    requests.post(f"{API}/quizzes/sessions/{session_id}/advance", headers=H)
    w(HOST); snap("21-control-q2", 3)
    w(PART); snap("22-participant-q2", 2)
    w(PRES); snap("23-present-q2", 1)

    requests.post(f"{API}/quizzes/sessions/{session_id}/toggle-leaderboard", headers=H)
    w(PART); snap("24-participant-leaderboard", 3); dump("24-participant-leaderboard")
    w(PRES); snap("25-present-leaderboard", 1.5)

    # --- end session
    requests.post(f"{API}/quizzes/sessions/{session_id}/end", headers=H)
    session_id = None
    w(PART); snap("26-participant-session-ended", 3); dump("26-participant-session-ended")
    w(HOST)
    d.get(f"{BASE}/quiz/{QUIZ_ID}/history")
    snap("27-history-after-session", 3); dump("27-history-after-session")
    rows = [e for e in d.find_elements(By.CSS_SELECTOR, "button, a") if e.is_displayed() and ("result" in e.text.lower() or "view" in e.text.lower())]
    if rows:
        rows[0].click(); snap("28-session-results", 3); dump("28-session-results")

    # --- exam + offline poll in participant window
    w(PART)
    d.get(EXAM_URL); snap("30-exam-entry", 4); dump("30-exam-entry")
    d.get(POLL_URL); snap("31-offline-poll", 4); dump("31-offline-poll")

    # --- theme picker
    w(HOST)
    d.get(f"{BASE}/dashboard"); time.sleep(3)
    icons = d.find_elements(By.CSS_SELECTOR, ".anticon-bg-colors")
    if icons:
        icons[0].click(); snap("40-theme-picker-open", 1.5); dump("40-theme-picker-open")
        items = [i for i in d.find_elements(By.CSS_SELECTOR, ".ant-dropdown-menu-item") if i.is_displayed()]
        print("themes:", [i.text for i in items])
        funky = [i for i in items if "funky" in i.text.lower()]
        if funky:
            funky[0].click(); snap("41-dashboard-funky", 2.5)
        d.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)

    # --- account menu
    avs = [e for e in d.find_elements(By.CSS_SELECTOR, ".anticon-user") if e.is_displayed()]
    if avs:
        avs[-1].click(); snap("42-account-menu", 1.5); dump("42-account-menu")

    print("PASS 2 DONE")
finally:
    if session_id:
        try: requests.post(f"{API}/quizzes/sessions/{session_id}/end", headers=H)
        except Exception: pass
    d.quit()

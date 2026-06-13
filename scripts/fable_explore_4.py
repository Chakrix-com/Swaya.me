"""Fable review pass 4 (test.swaya.me): proper live answer flow + exam end-to-end + history detail."""
import time, os, re, requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://test.swaya.me"
API = f"{BASE}/api/v1"
OUT = "/tmp/fable-review"
QUIZ_ID = 11

tok = requests.post(f"{API}/auth/login", json={"email": "demo@swaya.me", "password": "Demo1234"}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

o = webdriver.ChromeOptions()
o.add_argument("--no-sandbox"); o.add_argument("--disable-dev-shm-usage")
o.add_argument("--window-size=1440,900")
d = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=o)
wait = WebDriverWait(d, 15)

def snap(name, delay=1.5, bottom=False):
    time.sleep(delay)
    if bottom:
        d.execute_script("window.scrollTo(0, document.body.scrollHeight)"); time.sleep(0.7)
    d.save_screenshot(os.path.join(OUT, f"{name}.png"))
    print(f"  snap {name}.png url={d.current_url}")

def dump(name):
    open(os.path.join(OUT, f"{name}.txt"), "w").write(d.execute_script("return document.body.innerText"))

def click_btn(label):
    for b in d.find_elements(By.CSS_SELECTOR, "button"):
        if b.is_displayed() and label.lower() in (b.text or '').strip().lower():
            d.execute_script("arguments[0].scrollIntoView({block:'center'})", b); time.sleep(0.4)
            b.click(); return True
    return False

def js_click_text(pattern):
    return d.execute_script("""
      const re = new RegExp(arguments[0]);
      const els = Array.from(document.querySelectorAll('div,button,label,span'))
        .filter(e => e.offsetParent && e.innerText && re.test(e.innerText.trim()) && e.innerText.length < 60);
      if (!els.length) return null;
      const t = els[els.length - 1];  // deepest/last match
      t.click(); return t.innerText.slice(0, 40);
    """, pattern)

session_id = None
temp_id = None
try:
    d.get(f"{BASE}/login"); time.sleep(2)
    ins = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    ins[0].send_keys("demo@swaya.me")
    [i for i in ins if i.get_attribute("type") == "password"][0].send_keys("Demo1234")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard")); time.sleep(2)
    HOST = d.current_window_handle
    d.switch_to.new_window('window'); PART = d.current_window_handle
    d.set_window_size(430, 880)
    def w(h): d.switch_to.window(h); time.sleep(0.3)

    # ===== A. live quiz proper =====
    w(HOST)
    d.get(f"{BASE}/quiz/{QUIZ_ID}/control"); time.sleep(3)
    click_btn("Start Session"); time.sleep(3)
    code = d.execute_script("const m=document.body.innerText.match(/Join Code\\s*\\n?\\s*(\\d{4,8})/); return m?m[1]:null;")
    print("code:", code)
    sl = requests.get(f"{API}/quizzes/{QUIZ_ID}/sessions", headers=H).json().get("sessions", [])
    live = [s for s in sl if s.get("status") != "ended"]
    if not live:
        raise RuntimeError(f"Start Session click failed; page code={code}")
    session_id = max(s["id"] for s in live)
    snap("a01-control-ready-bottom", 0.5, bottom=True); dump("a01-control-ready")

    w(PART)
    d.get(f"{BASE}/join"); time.sleep(2)
    ins = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed()]
    ins[0].send_keys(str(code))
    if len(ins) > 1: ins[1].send_keys("Fable Reviewer")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click(); time.sleep(3)

    w(HOST)
    click_btn("Start First Question")
    snap("a02-control-q1-bottom", 3, bottom=True); dump("a02-control-q1")

    w(PART); time.sleep(1.5)
    print("clicked:", js_click_text("Paris$")); time.sleep(0.8)
    click_btn("Submit Answer")
    snap("a03-participant-correct-feedback", 2.5); dump("a03-participant-correct-feedback")

    w(HOST)
    snap("a04-control-q1-responses", 1.5, bottom=True); dump("a04-control-q1-responses")
    click_btn("Next Question")
    time.sleep(2.5)
    w(PART); time.sleep(1)
    # answer wrong on purpose (first option)
    print("clicked:", js_click_text("^A:")); time.sleep(0.8)
    click_btn("Submit Answer")
    snap("a05-participant-wrong-feedback", 2.5); dump("a05-participant-wrong-feedback")

    # leaderboard
    requests.post(f"{API}/quizzes/sessions/{session_id}/toggle-leaderboard", headers=H)
    snap("a06-participant-leaderboard", 3); dump("a06-participant-leaderboard")
    w(HOST)
    snap("a07-control-leaderboard", 1.5); dump("a07-control-leaderboard")

    # stop via UI
    click_btn("Stop Quiz"); time.sleep(1)
    for b in d.find_elements(By.CSS_SELECTOR, ".ant-modal button, .ant-popconfirm button, .ant-popover button"):
        if b.is_displayed() and b.text.strip().lower() in ("yes", "ok", "stop", "confirm"):
            b.click(); break
    time.sleep(2)
    snap("a08-control-after-stop", 1); dump("a08-control-after-stop")
    session_id = None
    w(PART)
    snap("a09-participant-final", 2); dump("a09-participant-final")

    # history expanded
    w(HOST)
    d.get(f"{BASE}/quiz/{QUIZ_ID}/history"); time.sleep(3)
    rows = d.find_elements(By.CSS_SELECTOR, ".anticon-right, [class*='expand']")
    if rows:
        rows[0].click()
    snap("a10-history-expanded", 2.5); dump("a10-history-expanded")

    # ===== B. exam end-to-end =====
    r = requests.post(f"{API}/quizzes/", headers=H, json={"title": "Fable Review Temp Exam", "description": "temp — will be deleted", "quiz_type": "exam"})
    print("create exam:", r.status_code)
    temp_id = r.json()["id"]
    for qtext, opts_, corr in [
        ("What is 2 + 2?", ["3", "4", "5", "22"], 1),
        ("Which planet is known as the Red Planet?", ["Venus", "Mars", "Jupiter", "Saturn"], 1),
    ]:
        r = requests.post(f"{API}/quizzes/{temp_id}/questions", headers=H, json={
            "question_type": "mcq", "text": qtext, "options": opts_,
            "correct_answer_index": corr, "points": 1, "max_time_seconds": 60,
        })
        print("add q:", r.status_code, r.text[:100])

    # publish via builder UI to capture the real host journey
    w(HOST)
    d.get(f"{BASE}/quiz/{temp_id}/edit"); time.sleep(3)
    snap("b01-exam-builder", 1); dump("b01-exam-builder")
    snap("b02-exam-builder-bottom", 0.3, bottom=True)
    pub = click_btn("Publish")
    print("clicked publish:", pub); time.sleep(2)
    snap("b03-exam-publish-modal", 1); dump("b03-exam-publish-modal")
    for b in d.find_elements(By.CSS_SELECTOR, ".ant-modal button"):
        if b.is_displayed() and b.text.strip().lower() in ("publish", "ok", "confirm", "yes"):
            b.click(); break
    time.sleep(3)
    snap("b04-exam-published", 1); dump("b04-exam-published")
    q = requests.get(f"{API}/quizzes/{temp_id}", headers=H).json()
    exam_url = q.get("exam_url")
    print("exam_url:", exam_url)
    if not exam_url:
        # fall back to API publish
        r = requests.post(f"{API}/quizzes/{temp_id}/publish-offline", headers=H,
                          json={"exam_start_at": "2026-06-11T00:00:00", "exam_end_at": "2026-06-12T00:00:00"})
        print("api publish-offline:", r.status_code, r.text[:200])
        q = requests.get(f"{API}/quizzes/{temp_id}", headers=H).json()
        exam_url = q.get("exam_url")
        print("exam_url2:", exam_url)

    if exam_url:
        w(PART)
        d.get(exam_url)
        snap("b05-exam-entry", 3); dump("b05-exam-entry")
        ins = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed()]
        for i_ in ins:
            ph = ((i_.get_attribute("placeholder") or '') + (i_.get_attribute("type") or '')).lower()
            if "email" in ph: i_.send_keys("fable@example.com")
            elif "name" in ph or i_ is ins[0]: i_.send_keys("Fable Reviewer")
        snap("b06-exam-entry-filled", 1)
        for lbl in ("Start", "Begin", "Continue"):
            if click_btn(lbl): break
        snap("b07-exam-q1", 3); dump("b07-exam-q1")
        print("exam clicked:", js_click_text("^(B[:.)]?\\s*)?4$")); time.sleep(0.8)
        snap("b08-exam-q1-selected", 1)
        for lbl in ("Next",):
            click_btn(lbl)
        time.sleep(1.5)
        print("exam clicked2:", js_click_text("Mars$")); time.sleep(0.8)
        snap("b09-exam-q2-selected", 1); dump("b09-exam-q2")
        for lbl in ("Submit", "Finish"):
            if click_btn(lbl): break
        time.sleep(1)
        for b in d.find_elements(By.CSS_SELECTOR, ".ant-modal button"):
            if b.is_displayed() and b.text.strip().lower() in ("yes", "ok", "submit", "confirm"):
                b.click(); break
        snap("b10-exam-submitted", 3); dump("b10-exam-submitted")

        w(HOST)
        d.get(f"{BASE}/quiz/{temp_id}/exam-results")
        snap("b11-exam-results-host", 4); dump("b11-exam-results-host")

    print("PASS 4 DONE")
finally:
    if session_id:
        try: requests.post(f"{API}/quizzes/sessions/{session_id}/end", headers=H)
        except Exception: pass
    if temp_id:
        try:
            requests.post(f"{API}/quizzes/{temp_id}/unpublish", headers=H)
            r = requests.delete(f"{API}/quizzes/{temp_id}", headers=H)
            print("cleanup:", r.status_code)
        except Exception as e:
            print("cleanup failed:", e)
    d.quit()

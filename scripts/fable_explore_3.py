"""Fable review pass 3 (test.swaya.me):
- redo live quiz with correct participant answers (host UI start/stop)
- live poll session for question-type variety (word cloud etc.)
- create temp exam via builder UI, publish, take as participant, delete
- dashboard create/template modals, mobile home
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
QUIZ_ID = 11      # Demo Quiz - General Knowledge
POLL_ID = 46      # New Question Types Test (poll, 4 q)

tok = requests.post(f"{API}/auth/login", json={"email": "demo@swaya.me", "password": "Demo1234"}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

o = webdriver.ChromeOptions()
o.add_argument("--no-sandbox"); o.add_argument("--disable-dev-shm-usage")
o.add_argument("--window-size=1440,900")
o.add_argument("--use-fake-ui-for-media-stream")
o.add_argument("--use-fake-device-for-media-stream")
d = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=o)
wait = WebDriverWait(d, 15)

def snap(name, delay=1.5):
    time.sleep(delay)
    d.save_screenshot(os.path.join(OUT, f"{name}.png"))
    print(f"  snap {name}.png url={d.current_url}")

def dump(name):
    open(os.path.join(OUT, f"{name}.txt"), "w").write(d.execute_script("return document.body.innerText"))

def vis_buttons():
    return [b for b in d.find_elements(By.CSS_SELECTOR, "button") if b.is_displayed()]

def click_btn(label, contains=True):
    for b in vis_buttons():
        t = (b.text or '').strip().lower()
        if (contains and label.lower() in t) or t == label.lower():
            d.execute_script("arguments[0].scrollIntoView({block:'center'})", b); time.sleep(0.3)
            b.click(); return True
    return False

session_ids = []
temp_quiz_id = None
try:
    # ---- login
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

    # ===== A. dashboard modals =====
    w(HOST)
    d.get(f"{BASE}/dashboard"); time.sleep(3)
    if click_btn("Create New"):
        snap("50-create-new-modal", 1.5); dump("50-create-new-modal")
        d.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE); time.sleep(0.8)
    if click_btn("Use Template"):
        snap("51-template-gallery", 2); dump("51-template-gallery")
        d.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE); time.sleep(0.8)

    # ===== B. live QUIZ redo with proper answers =====
    d.get(f"{BASE}/quiz/{QUIZ_ID}/control"); time.sleep(3)
    click_btn("Start Session")
    time.sleep(3); snap("52-control-started-ui", 1); dump("52-control-started-ui")
    # join code from page
    code = d.execute_script("""
      const m = document.body.innerText.match(/Join Code\\s*\\n?\\s*(\\d{4,8})/);
      return m ? m[1] : null;
    """)
    print("join code from UI:", code)
    sess = requests.get(f"{API}/quizzes/{QUIZ_ID}/sessions", headers=H).json()
    cur = [s for s in (sess if isinstance(sess, list) else sess.get('items', [])) if s.get('status') in ('created','active','started')]
    sid = cur[0]['id'] if cur else None
    if sid: session_ids.append(sid)
    print("session id:", sid)

    w(PART)
    d.get(f"{BASE}/join"); time.sleep(2)
    ins = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed()]
    ins[0].send_keys(str(code))
    if len(ins) > 1: ins[1].send_keys("Fable Reviewer")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(3)

    # host advances Q1 via UI
    w(HOST)
    for lbl in ("Next Question", "Start Quiz", "Next", "Advance"):
        if click_btn(lbl): break
    snap("53-control-q1-ui", 3); dump("53-control-q1-ui")

    # participant answers properly: click option box containing 'Paris'
    w(PART)
    time.sleep(1.5)
    ok = d.execute_script("""
      const els = Array.from(document.querySelectorAll('div,button,label'));
      const t = els.find(e => e.innerText && e.innerText.trim().match(/Paris$/) && e.offsetParent);
      if (t) { t.click(); return true } return false;
    """)
    print("clicked Paris:", ok)
    time.sleep(1)
    click_btn("Submit Answer")
    snap("54-participant-after-submit", 2.5); dump("54-participant-after-submit")

    w(HOST); snap("55-control-q1-responses", 2); dump("55-control-q1-responses")
    # reveal/next
    for lbl in ("Show Results", "Reveal", "Next Question", "Next"):
        if click_btn(lbl): break
    snap("56-control-after-reveal", 2.5)
    w(PART); snap("57-participant-result-state", 2); dump("57-participant-result-state")

    # leaderboard visible to participant?
    w(HOST)
    requests.post(f"{API}/quizzes/sessions/{sid}/toggle-leaderboard", headers=H)
    w(PART); snap("58-participant-leaderboard", 3); dump("58-participant-leaderboard")

    # stop quiz via UI
    w(HOST)
    click_btn("Stop Quiz"); time.sleep(1)
    # confirm modal
    for b in vis_buttons():
        if b.text.strip().lower() in ("yes", "ok", "stop", "confirm", "yes, stop"):
            b.click(); break
    snap("59-control-stopped", 3); dump("59-control-stopped")
    session_ids = [s for s in session_ids if s != sid]
    w(PART); snap("60-participant-after-stop", 2); dump("60-participant-after-stop")

    # ===== C. live POLL for question variety =====
    s = requests.post(f"{API}/quizzes/sessions/start", params={"quiz_id": POLL_ID}, headers=H).json()
    psid = s.get("id"); pcode = s.get("join_code"); session_ids.append(psid)
    print("poll session", psid, pcode)
    w(PART)
    d.get(f"{BASE}/join"); time.sleep(2)
    ins = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed()]
    ins[0].send_keys(str(pcode));
    if len(ins) > 1: ins[1].send_keys("Fable Reviewer")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(2.5)
    for qn in range(1, 5):
        requests.post(f"{API}/quizzes/sessions/{psid}/advance", headers=H)
        w(PART); snap(f"61-poll-q{qn}", 3); dump(f"61-poll-q{qn}")
    w(HOST)
    d.get(f"{BASE}/quiz/{POLL_ID}/control")
    snap("62-poll-control", 4); dump("62-poll-control")
    requests.post(f"{API}/quizzes/sessions/{psid}/end", headers=H)
    session_ids = [s for s in session_ids if s != psid]

    # ===== D. temp exam via builder UI =====
    w(HOST)
    d.get(f"{BASE}/quiz/new?type=exam"); time.sleep(3)
    snap("70-exam-builder-blank", 1); dump("70-exam-builder-blank")
    # title
    tins = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and "title" in (i.get_attribute("placeholder") or '').lower()]
    if not tins:
        tins = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed()]
    tins[0].send_keys("Fable Review Temp Exam")
    creators = [b for b in vis_buttons() if "create" in b.text.lower()]
    if creators: creators[0].click()
    time.sleep(3)
    snap("71-exam-builder-created", 1); dump("71-exam-builder-created")
    # capture current quiz id from URL
    import re
    m = re.search(r"/quiz/(\d+)/", d.current_url)
    if m: temp_quiz_id = int(m.group(1))
    print("temp exam id:", temp_quiz_id)

    if temp_quiz_id:
        # add 2 questions via API (builder modal automation is brittle), then reload builder to see them
        for qtext, opts_, corr in [
            ("What is 2 + 2?", ["3", "4", "5", "22"], 1),
            ("Which planet is known as the Red Planet?", ["Venus", "Mars", "Jupiter", "Saturn"], 1),
        ]:
            r = requests.post(f"{API}/quizzes/{temp_quiz_id}/questions", headers=H, json={
                "question_text": qtext, "question_type": "multiple_choice",
                "options": [{"option_text": t, "is_correct": i == corr} for i, t in enumerate(opts_)],
                "time_limit": 30, "points": 10,
            })
            print("add q:", r.status_code, r.text[:120])
        d.get(f"{BASE}/quiz/{temp_quiz_id}/edit"); time.sleep(3)
        snap("72-exam-builder-with-questions", 1); dump("72-exam-builder-with-questions")
        # open Add Question modal for a screenshot of the editor
        if click_btn("Add Question"):
            snap("73-question-editor-modal", 2); dump("73-question-editor-modal")
            d.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE); time.sleep(1)
        # publish via UI
        for lbl in ("Publish", "Publish Test", "Publish Exam"):
            if click_btn(lbl): break
        time.sleep(2)
        snap("74-exam-publish-dialog", 1); dump("74-exam-publish-dialog")
        # confirm in modal if present
        for b in vis_buttons():
            if b.text.strip().lower() in ("publish", "ok", "confirm", "yes") and b.find_elements(By.XPATH, "./ancestor::*[contains(@class,'ant-modal')]"):
                b.click(); break
        time.sleep(3)
        snap("75-exam-published", 1); dump("75-exam-published")
        q = requests.get(f"{API}/quizzes/{temp_quiz_id}", headers=H).json()
        exam_url = q.get("exam_url")
        print("exam_url:", exam_url)

        if exam_url:
            w(PART)
            d.get(exam_url)
            snap("76-exam-entry", 3); dump("76-exam-entry")
            ins = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed()]
            for i_ in ins:
                ph = (i_.get_attribute("placeholder") or '').lower()
                if "name" in ph: i_.send_keys("Fable Reviewer")
                elif "email" in ph or i_.get_attribute("type") == "email": i_.send_keys("fable@example.com")
            if ins and not any("name" in (i_.get_attribute("placeholder") or '').lower() for i_ in ins):
                ins[0].send_keys("Fable Reviewer")
            for lbl in ("Start", "Begin", "Take Test", "Continue"):
                if click_btn(lbl): break
            snap("77-exam-started", 3); dump("77-exam-started")
            # answer q1
            d.execute_script("""
              const els = Array.from(document.querySelectorAll('div,button,label'));
              const t = els.find(e => e.innerText && e.innerText.trim().match(/^(B[:.)]?\\s*)?4$/) && e.offsetParent);
              if (t) t.click();
            """)
            time.sleep(1)
            snap("78-exam-q1-answered", 1); dump("78-exam-q1-answered")
            for lbl in ("Next", "Save"):
                if click_btn(lbl): break
            time.sleep(1.5)
            d.execute_script("""
              const els = Array.from(document.querySelectorAll('div,button,label'));
              const t = els.find(e => e.innerText && /Mars$/.test(e.innerText.trim()) && e.offsetParent);
              if (t) t.click();
            """)
            time.sleep(1)
            for lbl in ("Submit", "Finish"):
                if click_btn(lbl): break
            time.sleep(1)
            for b in vis_buttons():
                if b.text.strip().lower() in ("yes", "ok", "submit", "confirm", "yes, submit"):
                    b.click(); break
            snap("79-exam-submitted", 3); dump("79-exam-submitted")

            # host: exam results page
            w(HOST)
            d.get(f"{BASE}/quiz/{temp_quiz_id}/exam-results")
            snap("80-exam-results-host", 4); dump("80-exam-results-host")

    # ===== E. mobile home =====
    w(PART)
    d.get(BASE); snap("90-home-mobile", 3)
    d.get(f"{BASE}/join"); snap("91-join-mobile", 2)

    print("PASS 3 DONE")
finally:
    for sid_ in session_ids:
        try: requests.post(f"{API}/quizzes/sessions/{sid_}/end", headers=H)
        except Exception: pass
    if temp_quiz_id:
        try:
            r = requests.delete(f"{API}/quizzes/{temp_quiz_id}", headers=H)
            print("cleanup temp exam:", r.status_code)
        except Exception as e:
            print("cleanup failed:", e)
    d.quit()

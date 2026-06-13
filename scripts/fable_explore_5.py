"""Fable review pass 5: exam-taking journey end-to-end with a temp exam (deleted afterwards)."""
import time, os, requests
from selenium import webdriver
from selenium.webdriver.common.by import By

BASE = "https://test.swaya.me"
API = f"{BASE}/api/v1"
OUT = "/tmp/fable-review"

tok = requests.post(f"{API}/auth/login", json={"email": "demo@swaya.me", "password": "Demo1234"}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

temp_id = None
d = None
try:
    r = requests.post(f"{API}/quizzes/", headers=H, json={"title": "Fable Review Temp Exam", "description": "temp — will be deleted", "quiz_type": "exam"})
    temp_id = r.json()["id"]
    for qtext, opts_, corr in [
        ("What is 2 + 2?", ["3", "4", "5", "22"], 1),
        ("Which planet is known as the Red Planet?", ["Venus", "Mars", "Jupiter", "Saturn"], 1),
    ]:
        requests.post(f"{API}/quizzes/{temp_id}/questions", headers=H, json={
            "question_type": "mcq", "text": qtext, "options": opts_,
            "correct_answer_index": corr, "points": 1, "max_time_seconds": 60})
    r = requests.put(f"{API}/quizzes/{temp_id}", headers=H, json={
        "exam_start_at": "2026-06-11T00:00:00", "exam_end_at": "2026-06-12T23:59:00"})
    print("set dates:", r.status_code, r.text[:150])
    r = requests.post(f"{API}/quizzes/{temp_id}/publish-exam", headers=H, json={})
    print("publish-exam:", r.status_code, r.text[:200])
    q = requests.get(f"{API}/quizzes/{temp_id}", headers=H).json()
    exam_url = q.get("exam_url")
    print("exam_url:", exam_url)
    assert exam_url

    o = webdriver.ChromeOptions()
    o.add_argument("--no-sandbox"); o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--window-size=430,880")
    o.add_argument("--use-fake-ui-for-media-stream"); o.add_argument("--use-fake-device-for-media-stream")
    d = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=o)

    def snap(name, delay=1.5):
        time.sleep(delay)
        d.save_screenshot(os.path.join(OUT, f"{name}.png"))
        print(f"  snap {name}.png url={d.current_url}")
    def dump(name):
        open(os.path.join(OUT, f"{name}.txt"), "w").write(d.execute_script("return document.body.innerText"))
    def click_btn(label):
        for b in d.find_elements(By.CSS_SELECTOR, "button"):
            if b.is_displayed() and label.lower() in (b.text or '').strip().lower():
                d.execute_script("arguments[0].scrollIntoView({block:'center'})", b); time.sleep(0.3)
                b.click(); return True
        return False
    def js_click_text(pattern):
        return d.execute_script("""
          const re = new RegExp(arguments[0]);
          const els = Array.from(document.querySelectorAll('div,button,label,span'))
            .filter(e => e.offsetParent && e.innerText && re.test(e.innerText.trim()) && e.innerText.length < 60);
          if (!els.length) return null;
          const t = els[els.length - 1]; t.click(); return t.innerText.slice(0, 40);
        """, pattern)

    d.get(exam_url)
    snap("c01-exam-entry", 3); dump("c01-exam-entry")
    ins = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed()]
    for i_ in ins:
        ph = ((i_.get_attribute("placeholder") or '') + ' ' + (i_.get_attribute("type") or '')).lower()
        if "email" in ph: i_.send_keys("fable@example.com")
        elif "name" in ph: i_.send_keys("Fable Reviewer")
    if ins and not ins[0].get_attribute("value"): ins[0].send_keys("Fable Reviewer")
    snap("c02-exam-entry-filled", 0.5)
    for lbl in ("Start", "Begin", "Continue", "Take"):
        if click_btn(lbl): break
    snap("c03-exam-started", 3); dump("c03-exam-started")
    print("q1:", js_click_text("^4$") or js_click_text("4")); time.sleep(0.8)
    snap("c04-exam-q1-selected", 0.5)
    click_btn("Next"); time.sleep(1.5)
    dump("c05-exam-q2")
    print("q2:", js_click_text("Mars$")); time.sleep(0.8)
    snap("c05-exam-q2-selected", 0.5)
    for lbl in ("Submit", "Finish"):
        if click_btn(lbl): break
    time.sleep(1)
    snap("c06-exam-submit-confirm", 0.5); dump("c06-exam-submit-confirm")
    for b in d.find_elements(By.CSS_SELECTOR, ".ant-modal button, .ant-modal-confirm-btns button"):
        if b.is_displayed() and b.text.strip().lower() in ("yes", "ok", "submit", "confirm"):
            b.click(); break
    snap("c07-exam-submitted", 3); dump("c07-exam-submitted")

    # host results
    d.set_window_size(1440, 900)
    d.get(f"{BASE}/login"); time.sleep(2)
    ins = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    if ins:
        ins[0].send_keys("demo@swaya.me")
        [i for i in ins if i.get_attribute("type") == "password"][0].send_keys("Demo1234")
        d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(4)
    d.get(f"{BASE}/quiz/{temp_id}/exam-results")
    snap("c08-exam-results-host", 4); dump("c08-exam-results-host")
    # expand a result row if present
    exp = d.find_elements(By.CSS_SELECTOR, ".anticon-right, [class*='expand'] button")
    if exp:
        exp[0].click(); snap("c09-exam-result-detail", 2); dump("c09-exam-result-detail")

    print("PASS 5 DONE")
finally:
    if temp_id:
        try:
            requests.post(f"{API}/quizzes/{temp_id}/unpublish-exam", headers=H)
        except Exception: pass
        try:
            r = requests.delete(f"{API}/quizzes/{temp_id}", headers=H)
            print("cleanup:", r.status_code)
        except Exception as e:
            print("cleanup failed:", e)
    if d: d.quit()

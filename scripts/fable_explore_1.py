"""Fable review exploration pass 1: public pages + login + dashboard on www.swaya.me (read-only)."""
import time, os, json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://test.swaya.me"
OUT = "/tmp/fable-review"
os.makedirs(OUT, exist_ok=True)

opts = webdriver.ChromeOptions()
opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1440,900")
d = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=opts)
wait = WebDriverWait(d, 15)

def snap(name, delay=1.5, full=False):
    time.sleep(delay)
    if full:
        h = d.execute_script("return Math.min(document.body.scrollHeight, 6000)")
        d.set_window_size(1440, max(900, h))
        time.sleep(0.8)
    p = os.path.join(OUT, f"{name}.png")
    d.save_screenshot(p)
    print(f"  snap {name}.png ({os.path.getsize(p)//1024}KB) url={d.current_url}")
    if full:
        d.set_window_size(1440, 900)
        time.sleep(0.5)

def dump_text(name):
    txt = d.execute_script("return document.body.innerText")
    with open(os.path.join(OUT, f"{name}.txt"), "w") as f:
        f.write(txt)
    print(f"  text {name}.txt ({len(txt)} chars)")

try:
    # --- 1. Public home page
    d.get(BASE)
    snap("01-home-top", 3)
    dump_text("01-home")
    snap("01b-home-full", 0.5, full=True)

    # --- 2. Join page (audience entry)
    d.get(f"{BASE}/join")
    snap("02-join", 2)
    dump_text("02-join")

    # --- 3. Login page
    d.get(f"{BASE}/login")
    snap("03-login", 2)
    dump_text("03-login")

    # login
    inputs = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    inputs[0].send_keys("demo@swaya.me")
    [i for i in inputs if i.get_attribute("type") == "password"][0].send_keys("Demo1234")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))
    snap("04-dashboard", 4)
    dump_text("04-dashboard")
    snap("04b-dashboard-full", 0.5, full=True)

    # save auth state for next passes
    state = {
        "local": d.execute_script("return JSON.stringify(localStorage)"),
        "cookies": d.get_cookies(),
    }
    with open(os.path.join(OUT, "auth_state.json"), "w") as f:
        json.dump(state, f)

    # list quiz cards / table rows on the dashboard
    links = d.execute_script("""
      return Array.from(document.querySelectorAll('a,button')).slice(0,200).map(e => ({
        tag: e.tagName, text: (e.innerText||'').trim().slice(0,60), href: e.getAttribute('href')
      })).filter(x => x.text);
    """)
    with open(os.path.join(OUT, "04-dashboard-controls.json"), "w") as f:
        json.dump(links, f, indent=1)
    print(f"  dashboard controls: {len(links)}")

    # --- 5. Plans page
    d.get(f"{BASE}/plans")
    snap("05-plans", 3)
    dump_text("05-plans")
    snap("05b-plans-full", 0.5, full=True)

    # --- 6. Quiz builder (new) — DO NOT SAVE
    d.get(f"{BASE}/quiz/new")
    snap("06-quiz-new", 3)
    dump_text("06-quiz-new")
    snap("06b-quiz-new-full", 0.5, full=True)

    print("PASS 1 DONE")
finally:
    d.quit()

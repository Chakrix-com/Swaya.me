"""End session 268 and screenshot the final leaderboard + results."""
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

# Check leaderboard data via API
lb = requests.get(f"{API}/quizzes/sessions/268/leaderboard", headers=h)
print("Leaderboard API:", lb.status_code, lb.text[:400])

opts = webdriver.ChromeOptions()
opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1280,900")
d = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=opts)
wait = WebDriverWait(d, 15)

def snap(name, delay=2):
    time.sleep(delay)
    p = os.path.join(OUT, f"{name}.png")
    d.save_screenshot(p)
    print(f"  ✓ {name}.png ({os.path.getsize(p)//1024}KB)")

try:
    d.get(f"{BASE}/login")
    time.sleep(2)
    inputs = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    inputs[0].send_keys("demo@swaya.me")
    [i for i in inputs if i.get_attribute("type") == "password"][0].send_keys("Demo1234")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))
    time.sleep(2)

    # Go to control page
    d.get(f"{BASE}/quiz/39/control")
    time.sleep(3)

    # Screenshot current state (question 2 open, leaderboard visible)
    snap("quiz_control_with_leaderboard", delay=1)

    # Scroll down to see leaderboard panel
    d.execute_script("window.scrollBy(0, 300)")
    snap("quiz_leaderboard_host", delay=1)

    # End the session
    btns = [b for b in d.find_elements(By.XPATH, "//button") if b.is_displayed() and b.is_enabled() and "End Session" in b.text]
    if btns:
        btns[0].click()
        time.sleep(1)
        confirm = [b for b in d.find_elements(By.XPATH, "//button") if b.is_displayed() and any(x in b.text for x in ["OK", "Yes", "Confirm", "End"])]
        if confirm:
            print(f"  Confirming: '{confirm[0].text}'")
            confirm[0].click()
            time.sleep(2)

    snap("quiz_session_ended", delay=2)

    # History
    d.get(f"{BASE}/quiz/39/history")
    time.sleep(3)
    snap("quiz_history_results", delay=1)

except Exception as e:
    import traceback; traceback.print_exc()
    try: d.save_screenshot(os.path.join(OUT, "_error_lb3.png"))
    except: pass
finally:
    d.quit()

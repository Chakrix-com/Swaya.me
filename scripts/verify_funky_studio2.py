"""Re-verify Funky-Studio after fixes: scrolled dashboard, public pages stay light,
and a quiz builder page sanity check under the dark theme."""
import time, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://test.swaya.me"
OUT = "/tmp/funky-studio"

opts = webdriver.ChromeOptions()
opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1400,900")
d = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=opts)
wait = WebDriverWait(d, 15)

def snap(name, delay=1.5):
    time.sleep(delay)
    d.save_screenshot(os.path.join(OUT, f"{name}.png"))
    print(f"  ✓ {name}.png")

try:
    d.get(f"{BASE}/login")
    time.sleep(2)
    inputs = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    inputs[0].send_keys("demo@swaya.me")
    [i for i in inputs if i.get_attribute("type") == "password"][0].send_keys("Demo1234")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))
    time.sleep(2)
    d.execute_script("localStorage.setItem('uiThemeId','funky-studio')")
    d.refresh()
    time.sleep(3)

    body_bg = d.execute_script("return getComputedStyle(document.body).backgroundColor")
    print("body bg:", body_bg)

    d.execute_script("document.querySelector('.dashboard-scroll').scrollTop = 700")
    snap("07-funky-dashboard-scrolled")

    # quiz builder under dark theme
    d.get(f"{BASE}/quiz/new?type=quiz")
    snap("08-funky-quiz-builder", 4)

    # public pages must be light again
    d.get(f"{BASE}/about")
    snap("09-about-light", 3)
    d.get(f"{BASE}/join")
    time.sleep(3)
    bg = d.execute_script("return getComputedStyle(document.querySelector('.visitor-theme')).backgroundColor")
    print("join visitor bg:", bg)
    snap("10-join-light", 1)

    print("DONE")
finally:
    d.quit()

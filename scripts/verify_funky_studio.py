"""Verify Funky-Studio theme on test.swaya.me: switch via picker, screenshot dashboard,
home page, and confirm participant pages stay light."""
import time, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://test.swaya.me"
OUT = "/tmp/funky-studio"
os.makedirs(OUT, exist_ok=True)

opts = webdriver.ChromeOptions()
opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1400,900")
d = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=opts)
wait = WebDriverWait(d, 15)

def snap(name, delay=1.5):
    time.sleep(delay)
    p = os.path.join(OUT, f"{name}.png")
    d.save_screenshot(p)
    print(f"  ✓ {name}.png")

try:
    # login
    d.get(f"{BASE}/login")
    time.sleep(2)
    inputs = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    inputs[0].send_keys("demo@swaya.me")
    [i for i in inputs if i.get_attribute("type") == "password"][0].send_keys("Demo1234")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))
    time.sleep(3)
    snap("01-classic-dashboard")

    # open picker, choose Funky-Studio
    d.find_element(By.CSS_SELECTOR, ".anticon-bg-colors").click()
    time.sleep(1)
    items = d.find_elements(By.CSS_SELECTOR, ".ant-dropdown-menu-item")
    print("picker items:", [i.text for i in items if i.is_displayed()])
    [i for i in items if "Funky-Studio" in i.text][0].click()
    time.sleep(2)
    assert d.execute_script("return localStorage.getItem('uiThemeId')") == "funky-studio"
    assert d.execute_script("return document.documentElement.dataset.theme") == "funky-studio"
    snap("02-funky-dashboard-top")
    d.execute_script("document.querySelector('.dashboard-scroll').scrollTop = 600; window.scrollTo(0,600)")
    snap("03-funky-dashboard-mid")

    # profile dropdown legibility
    d.execute_script("window.scrollTo(0,0)")
    d.find_elements(By.CSS_SELECTOR, ".ant-pro-global-header-header-actions-avatar, .ant-avatar")[-1].click()
    snap("04-funky-profile-menu")
    d.find_element(By.TAG_NAME, "body").send_keys(u'')  # ESC

    # public home page (same browser keeps the theme)
    d.get(f"{BASE}/about")
    snap("05-funky-about", 3)

    # participant page must stay light
    d.get(f"{BASE}/join")
    snap("06-join-still-light", 3)

    bg = d.execute_script("return getComputedStyle(document.querySelector('.visitor-theme')).backgroundColor")
    print("join page visitor bg:", bg)

    print("ALL CHECKS DONE")
finally:
    d.quit()

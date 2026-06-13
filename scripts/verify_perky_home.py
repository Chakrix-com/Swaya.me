"""Verify: new Home design in all 3 themes + Perky-Game app theming on test.swaya.me."""
import time, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://test.swaya.me"
OUT = "/tmp/perky"
os.makedirs(OUT, exist_ok=True)

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
    # 1. anonymous home = classic palette, new design
    d.get(BASE)
    snap("01-home-classic", 4)

    # 2. login, check picker has 3 themes
    d.get(f"{BASE}/login")
    time.sleep(2)
    inputs = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    inputs[0].send_keys("demo@swaya.me")
    [i for i in inputs if i.get_attribute("type") == "password"][0].send_keys("Demo1234")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))
    time.sleep(2)
    d.find_element(By.CSS_SELECTOR, ".anticon-bg-colors").click()
    time.sleep(1)
    items = [i.text for i in d.find_elements(By.CSS_SELECTOR, ".ant-dropdown-menu-item") if i.is_displayed()]
    print("picker:", items)
    assert any("Perky-Game" in t for t in items), "Perky-Game missing from picker"
    snap("02-picker-three")

    # 3. switch to Perky-Game → dashboard
    [i for i in d.find_elements(By.CSS_SELECTOR, ".ant-dropdown-menu-item") if "Perky-Game" in i.text][0].click()
    time.sleep(2.5)
    assert d.execute_script("return document.documentElement.dataset.theme") == "perky-game"
    snap("03-perky-dashboard")

    # 4. home in Perky-Game (same browser, logged out view via direct nav while logged in -> home redirects to dashboard?
    # Home route '/' redirects to /dashboard when authenticated; so test home by clearing auth but keeping theme.
    d.execute_script("localStorage.removeItem('token'); localStorage.removeItem('user');")
    d.get(BASE)
    snap("04-home-perky", 4)

    # 5. home in Funky-Studio
    d.execute_script("localStorage.setItem('uiThemeId','funky-studio')")
    d.refresh()
    snap("05-home-funky", 4)

    # 6. home scrolled (perky) — sections
    d.execute_script("localStorage.setItem('uiThemeId','perky-game')")
    d.refresh()
    time.sleep(3)
    d.execute_script("window.scrollTo(0, 1000)")
    snap("06-home-perky-modes", 1.5)
    d.execute_script("window.scrollTo(0, 2400)")
    snap("07-home-perky-trust", 1.5)

    print("ALL CHECKS DONE")
finally:
    d.quit()

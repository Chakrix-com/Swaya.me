"""Verify the new ThemePicker on test.swaya.me: login, open picker, select Classic Indigo."""
import time, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://test.swaya.me"
OUT = "/tmp/theme-picker"
os.makedirs(OUT, exist_ok=True)

opts = webdriver.ChromeOptions()
opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1400,900")
d = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=opts)
wait = WebDriverWait(d, 15)

def snap(name, delay=1):
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
    time.sleep(3)
    snap("01-dashboard")

    # Find the theme picker button (BgColorsOutlined icon)
    btns = d.find_elements(By.CSS_SELECTOR, ".anticon-bg-colors")
    print(f"theme picker icon found: {len(btns)}")
    assert btns, "ThemePicker button not found in header"
    btns[0].click()
    time.sleep(1)
    snap("02-picker-open")

    # Dropdown should list Classic Indigo
    items = d.find_elements(By.CSS_SELECTOR, ".ant-dropdown-menu-item")
    texts = [i.text for i in items if i.is_displayed()]
    print("dropdown items:", texts)
    assert any("Classic Indigo" in t for t in texts), "Classic Indigo not in picker"

    # Select it and confirm persistence
    [i for i in items if "Classic Indigo" in i.text][0].click()
    time.sleep(1)
    stored = d.execute_script("return localStorage.getItem('uiThemeId')")
    print("localStorage uiThemeId =", stored)
    assert stored == "classic-indigo"
    snap("03-after-select")

    print("ALL CHECKS PASSED")
finally:
    d.quit()

"""
Capture export dropdown screenshot — waits for the actual Ant Design dropdown to appear.
"""
import time, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://test.swaya.me"
OUT  = "/home/vinay/Swaya.me/frontend/public/assets/help-screens"

opts = webdriver.ChromeOptions()
opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1280,860")
d = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=opts)
wait = WebDriverWait(d, 15)

def snap(name, delay=0):
    time.sleep(delay)
    p = os.path.join(OUT, f"{name}.png")
    d.save_screenshot(p)
    print(f"  ✓ {name}.png ({os.path.getsize(p)//1024}KB)")

try:
    # Login
    d.get(f"{BASE}/login")
    time.sleep(2)
    inputs = [i for i in d.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    inputs[0].send_keys("demo@swaya.me")
    [i for i in inputs if i.get_attribute("type") == "password"][0].send_keys("Demo1234")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))
    time.sleep(2)

    # Go to quiz 39 history
    d.get(f"{BASE}/quiz/39/history")
    time.sleep(3)

    # Find all Export buttons
    export_btns = [b for b in d.find_elements(By.XPATH, "//button[normalize-space(text())='Export' or .//span[normalize-space(text())='Export']]") if b.is_displayed()]
    print(f"  Found {len(export_btns)} Export buttons")

    if not export_btns:
        print("  No export buttons found!")
        snap("_no_export_btns")
        d.quit()
        exit()

    # Use the first Export button — scroll it to near the top of the viewport
    btn = export_btns[0]
    # Scroll so button is ~200px from the top (room below for dropdown)
    d.execute_script("""
        var el = arguments[0];
        var rect = el.getBoundingClientRect();
        var targetTop = 200;
        window.scrollBy(0, rect.top - targetTop);
    """, btn)
    time.sleep(0.8)

    print(f"  Button position after scroll: {btn.location}")
    snap("quiz_history_before_click", delay=0.2)

    # Click via JavaScript to avoid any overlay issues
    d.execute_script("arguments[0].click()", btn)
    print("  Clicked Export button")

    # Wait for the Ant Design dropdown to appear
    # Ant Design Dropdown renders as .ant-dropdown (without ant-dropdown-hidden class)
    try:
        dropdown = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-dropdown:not(.ant-dropdown-hidden)"))
        )
        print(f"  Dropdown appeared! visible={dropdown.is_displayed()}")
        # List items inside
        items = dropdown.find_elements(By.CSS_SELECTOR, "li")
        for item in items:
            if item.is_displayed():
                print(f"    Item: '{item.text.strip()}'")
    except Exception as e:
        print(f"  Dropdown wait timeout: {e}")
        # List all ant-dropdown elements
        dropdowns = d.find_elements(By.CSS_SELECTOR, ".ant-dropdown")
        print(f"  All .ant-dropdown elements: {len(dropdowns)}")
        for dd in dropdowns:
            print(f"    visible={dd.is_displayed()} class='{dd.get_attribute('class')}'")
            print(f"    text='{dd.text[:100]}'")

    snap("quiz_export_dropdown", delay=0.3)
    print("  Dropdown screenshot taken")

    print("\nDone!")

except Exception as e:
    import traceback; traceback.print_exc()
    try: d.save_screenshot(os.path.join(OUT, "_err_export3.png"))
    except: pass
finally:
    d.quit()

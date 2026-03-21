"""
Debug export dropdown — use regular click, JS to inspect DOM, then screenshot.
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

    d.get(f"{BASE}/quiz/39/history")
    time.sleep(3)

    # Find Export buttons
    export_btns = [b for b in d.find_elements(By.XPATH, "//button[normalize-space(text())='Export' or .//span[normalize-space(text())='Export']]") if b.is_displayed()]
    print(f"  Found {len(export_btns)} Export buttons")

    btn = export_btns[0]
    # Scroll button to y=250 from top (plenty of room below)
    d.execute_script("""
        var el = arguments[0];
        var rect = el.getBoundingClientRect();
        window.scrollBy(0, rect.top - 250);
    """, btn)
    time.sleep(1)
    print(f"  Button rect: {d.execute_script('return arguments[0].getBoundingClientRect()', btn)}")

    # Use regular Selenium click (not JS click)
    btn.click()
    print("  Clicked Export button (regular click)")
    time.sleep(2)

    # Inspect DOM for any new elements
    result = d.execute_script("""
        var all = document.querySelectorAll('[class*="dropdown"], [class*="Dropdown"], [class*="popup"], [class*="Popup"], [class*="overlay"], [class*="menu"]');
        var info = [];
        for (var i=0; i<all.length; i++) {
            var el = all[i];
            var rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                info.push({
                    cls: el.className.substring(0,80),
                    text: el.textContent.substring(0,60),
                    x: rect.x, y: rect.y, w: rect.width, h: rect.height,
                    visible: el.style.display !== 'none' && el.style.visibility !== 'hidden'
                });
            }
        }
        return info;
    """)
    print(f"  Dropdown-related elements in DOM: {len(result)}")
    for r in result:
        print(f"    cls='{r['cls']}' x={r['x']:.0f} y={r['y']:.0f} w={r['w']:.0f} h={r['h']:.0f} text='{r['text'].strip()}'")

    snap("quiz_export_dropdown", delay=0.3)

    print("\nDone!")

except Exception as e:
    import traceback; traceback.print_exc()
    try: d.save_screenshot(os.path.join(OUT, "_err_export4.png"))
    except: pass
finally:
    d.quit()

"""
Capture export dropdown - try ActionChains click and immediate screenshot.
"""
import time, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

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

    export_btns = [b for b in d.find_elements(By.XPATH, "//button[normalize-space(text())='Export' or .//span[normalize-space(text())='Export']]") if b.is_displayed()]
    print(f"  Found {len(export_btns)} Export buttons")

    btn = export_btns[0]
    # Scroll button to middle area
    d.execute_script("""
        var el = arguments[0];
        var rect = el.getBoundingClientRect();
        window.scrollBy(0, rect.top - 300);
    """, btn)
    time.sleep(0.5)

    # Use ActionChains - move to element, then click
    actions = ActionChains(d)
    actions.move_to_element(btn).perform()
    time.sleep(0.5)
    actions.click(btn).perform()
    print("  Clicked with ActionChains")

    # Take screenshots at 0.2s, 0.5s, 1s, 2s intervals
    for delay_ms, label in [(200, "200ms"), (500, "500ms"), (1000, "1s"), (2000, "2s")]:
        time.sleep(delay_ms / 1000)

        # Check DOM
        result = d.execute_script("""
            // Check for any new elements in body that look like a popup
            var bodyChildren = Array.from(document.body.children);
            var popups = bodyChildren.filter(el => {
                var cls = el.className || '';
                return cls.includes('dropdown') || cls.includes('popup') || cls.includes('trigger') || cls.includes('overlay') || cls.includes('rc-');
            });
            return popups.map(el => ({
                cls: el.className.substring(0, 100),
                visible: window.getComputedStyle(el).display !== 'none',
                opacity: window.getComputedStyle(el).opacity,
                text: el.textContent.substring(0, 80)
            }));
        """)
        print(f"  At {label}: {len(result)} popup-like body children")
        for r in result:
            print(f"    visible={r['visible']} opacity={r['opacity']} cls='{r['cls']}' text='{r['text'].strip()}'")

        if not result:
            # Also check ALL body direct children
            all_body = d.execute_script("""
                return Array.from(document.body.children).map(el => ({
                    tag: el.tagName, cls: el.className.substring(0,60),
                    display: window.getComputedStyle(el).display
                }));
            """)
            print(f"  ALL body children ({len(all_body)}):")
            for c in all_body:
                print(f"    <{c['tag']} class='{c['cls']}' display={c['display']}>")

        snap(f"export_at_{label.replace('/', '')}", delay=0)

    print("\nDone!")

except Exception as e:
    import traceback; traceback.print_exc()
    try: d.save_screenshot(os.path.join(OUT, "_err_export5.png"))
    except: pass
finally:
    d.quit()

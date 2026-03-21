"""
Capture export dropdown - inspect body children deeply to find the Ant Design popup portal.
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
    d.execute_script("""
        var el = arguments[0];
        var rect = el.getBoundingClientRect();
        window.scrollBy(0, rect.top - 300);
    """, btn)
    time.sleep(0.5)

    actions = ActionChains(d)
    actions.move_to_element(btn).click(btn).perform()
    print("  Clicked Export button")
    time.sleep(0.5)

    # Check inside all body children
    result = d.execute_script("""
        var bodyChildren = Array.from(document.body.children);
        var info = [];
        bodyChildren.forEach(function(child, idx) {
            var clsName = child.className || '';
            var html = child.innerHTML.substring(0, 300);
            var rect = child.getBoundingClientRect();
            info.push({
                idx: idx,
                tag: child.tagName,
                cls: clsName.substring(0, 60),
                innerHtml: html,
                childCount: child.children.length,
                rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height}
            });
        });
        return info;
    """)
    for r in result:
        print(f"  Body child [{r['idx']}]: <{r['tag']} class='{r['cls']}' children={r['childCount']} rect=({r['rect']['x']:.0f},{r['rect']['y']:.0f},{r['rect']['w']:.0f},{r['rect']['h']:.0f})>")
        if r['childCount'] > 0:
            print(f"    innerHTML: {r['innerHtml'][:200]}")

    snap("quiz_export_dropdown", delay=0.3)
    print("  Screenshot taken")

    print("\nDone!")

except Exception as e:
    import traceback; traceback.print_exc()
    try: d.save_screenshot(os.path.join(OUT, "_err_export6.png"))
    except: pass
finally:
    d.quit()

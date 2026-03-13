"""
Capture export UI screenshots from QuizHistory page.
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

def snap(name, delay=1):
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

    # Go to quiz 39 history (has ended sessions)
    d.get(f"{BASE}/quiz/39/history")
    time.sleep(3)
    snap("quiz_history_page", delay=1)

    # Find and click the Download/Export button to open dropdown
    # Look for download icon button or button with download-related text
    export_btns = []
    for btn in d.find_elements(By.XPATH, "//button"):
        if not btn.is_displayed(): continue
        # Check for download icon or aria-label
        aria = btn.get_attribute("aria-label") or ""
        title = btn.get_attribute("title") or ""
        text = btn.text or ""
        cls = btn.get_attribute("class") or ""
        if any(x in (aria+title+text).lower() for x in ["download", "export"]):
            export_btns.append(btn)
            print(f"  Found export btn: text='{text}' aria='{aria}' title='{title}'")

    # Also look for antd dropdown buttons with download icon
    if not export_btns:
        # Try finding by icon class
        icon_btns = d.find_elements(By.XPATH, "//button[.//span[contains(@class,'anticon-download')]]")
        export_btns.extend([b for b in icon_btns if b.is_displayed()])
        print(f"  Found {len(icon_btns)} download icon buttons")

    if export_btns:
        # Click first one to open dropdown
        export_btns[0].click()
        time.sleep(1.5)
        snap("quiz_export_dropdown", delay=0.5)
        print("  Export dropdown opened")
    else:
        print("  No export button found — dumping visible buttons:")
        for btn in d.find_elements(By.XPATH, "//button"):
            if btn.is_displayed() and btn.text.strip():
                print(f"    '{btn.text.strip()[:40]}'")
        # Try clicking on first session to expand it
        collapse_hdrs = d.find_elements(By.CSS_SELECTOR, ".ant-collapse-header")
        if collapse_hdrs:
            collapse_hdrs[0].click()
            time.sleep(1.5)
            snap("quiz_history_expanded", delay=0.5)
            # Now try export again
            icon_btns = d.find_elements(By.XPATH, "//button[.//span[contains(@class,'anticon-download')]]")
            if icon_btns:
                icon_btns[0].click()
                time.sleep(1.5)
                snap("quiz_export_dropdown", delay=0.5)

    print("\nDone!")

except Exception as e:
    import traceback; traceback.print_exc()
    try: d.save_screenshot(os.path.join(OUT, "_err_export.png"))
    except: pass
finally:
    d.quit()

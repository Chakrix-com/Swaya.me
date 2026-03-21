"""
Capture export dropdown screenshot.
Strategy: scroll the Export button into view, click it, wait for dropdown, screenshot.
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
    snap("quiz_history_page", delay=1)

    # Find all visible buttons
    all_btns = [b for b in d.find_elements(By.XPATH, "//button") if b.is_displayed()]
    print(f"  Total visible buttons: {len(all_btns)}")
    for btn in all_btns:
        txt = btn.text.strip()
        aria = btn.get_attribute("aria-label") or ""
        title = btn.get_attribute("title") or ""
        cls = btn.get_attribute("class") or ""
        if txt or aria or title:
            print(f"    text='{txt[:40]}' aria='{aria[:30]}' title='{title[:30]}' class='{cls[:60]}'")

    # Find export/download button
    export_btn = None
    for btn in all_btns:
        aria = (btn.get_attribute("aria-label") or "").lower()
        title = (btn.get_attribute("title") or "").lower()
        text = (btn.text or "").lower()
        cls = (btn.get_attribute("class") or "").lower()
        if any(x in (aria + title + text) for x in ["export", "download"]):
            export_btn = btn
            print(f"  Found by text/aria: text='{btn.text}' aria='{btn.get_attribute('aria-label')}'")
            break

    # Also try anticon-download
    if not export_btn:
        icon_btns = [b for b in d.find_elements(By.XPATH, "//button[.//span[contains(@class,'anticon-download')]]") if b.is_displayed()]
        if icon_btns:
            export_btn = icon_btns[0]
            print(f"  Found by anticon-download: {len(icon_btns)} buttons")

    # Try anticon-export
    if not export_btn:
        icon_btns = [b for b in d.find_elements(By.XPATH, "//button[.//span[contains(@class,'anticon-export')]]") if b.is_displayed()]
        if icon_btns:
            export_btn = icon_btns[0]
            print(f"  Found by anticon-export: {len(icon_btns)} buttons")

    if not export_btn:
        # Try collapsing a session first
        print("  No export button visible — expanding first collapsed session row")
        rows = d.find_elements(By.CSS_SELECTOR, ".ant-table-row, tr")
        print(f"  Table rows: {len(rows)}")
        # Try clicking on ENDED badge/row to expand
        ended_els = [e for e in d.find_elements(By.XPATH, "//*[contains(text(),'ENDED') or contains(text(),'Ended')]") if e.is_displayed()]
        print(f"  ENDED elements: {len(ended_els)}")
        if ended_els:
            # Click the row containing the first ENDED badge
            try:
                row = ended_els[0].find_element(By.XPATH, "./ancestor::tr")
                row.click()
                time.sleep(1.5)
                # Re-find export button
                icon_btns = [b for b in d.find_elements(By.XPATH, "//button[.//span[contains(@class,'anticon-download') or contains(@class,'anticon-export')]]") if b.is_displayed()]
                if icon_btns:
                    export_btn = icon_btns[0]
                    print(f"  Found after row expand: {len(icon_btns)} buttons")
            except Exception as e:
                print(f"  Row click error: {e}")

    if export_btn:
        # Scroll the button to middle of viewport
        d.execute_script("arguments[0].scrollIntoView({block: 'center'})", export_btn)
        time.sleep(0.8)
        snap("quiz_history_export_btn_visible", delay=0.2)

        # Click Export button
        export_btn.click()
        print("  Clicked export button")

        # Wait longer for dropdown to appear
        time.sleep(2.5)

        # Check if dropdown appeared
        dropdown_items = d.find_elements(By.CSS_SELECTOR, ".ant-dropdown-menu-item, .ant-dropdown li, [role='menuitem']")
        visible_items = [item for item in dropdown_items if item.is_displayed()]
        print(f"  Dropdown items found: {len(dropdown_items)} total, {len(visible_items)} visible")
        for item in visible_items:
            print(f"    '{item.text.strip()}'")

        snap("quiz_export_dropdown", delay=0.3)
        print("  Export dropdown screenshot taken")
    else:
        print("  ERROR: No export button found at all — check quiz history page structure")
        d.save_screenshot(os.path.join(OUT, "_err_no_export_btn.png"))

    print("\nDone!")

except Exception as e:
    import traceback; traceback.print_exc()
    try: d.save_screenshot(os.path.join(OUT, "_err_export2.png"))
    except: pass
finally:
    d.quit()

"""Quick verification of the Help page."""
import time, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = webdriver.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1280,900")

driver = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=options)
wait = WebDriverWait(driver, 15)

try:
    print("Loading /help page...")
    driver.get("https://test.swaya.me/help")
    time.sleep(3)

    title = driver.title
    print(f"Page title: {title}")

    # Check sections exist
    for section_id in ['hosts', 'audience', 'question-types', 'faq']:
        try:
            el = driver.find_element(By.ID, section_id)
            print(f"  ✓ #{section_id} section found")
        except:
            print(f"  ✗ #{section_id} MISSING")

    # Screenshot the full page
    driver.save_screenshot("/home/vinay/Swaya.me/frontend/public/help/_verify_top.png")
    print("  ✓ Top screenshot saved")

    # Click "Show me how" on first host step
    btns = driver.find_elements(By.XPATH, "//*[contains(text(),'Show me how')]")
    print(f"  Found {len(btns)} 'Show me how' buttons")
    if btns:
        btns[0].click()
        time.sleep(2)
        driver.save_screenshot("/home/vinay/Swaya.me/frontend/public/help/_verify_expanded.png")
        print("  ✓ Expanded step screenshot saved")

    # Check screenshot images loaded
    imgs = driver.find_elements(By.CSS_SELECTOR, "img")
    broken = 0
    for img in imgs:
        if img.get_attribute('src') and '/help/' in img.get_attribute('src'):
            nat_w = driver.execute_script("return arguments[0].naturalWidth", img)
            if nat_w == 0:
                broken += 1
                print(f"  ✗ Broken image: {img.get_attribute('src')}")
    if broken == 0:
        print("  ✓ No broken help images detected")

    print("\nDone!")

except Exception as e:
    import traceback; traceback.print_exc()
finally:
    driver.quit()

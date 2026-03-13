"""
Capture Quiz vs Poll screenshots for Help Center.
"""
import time, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

BASE_URL = "https://test.swaya.me"
OUT = "/home/vinay/Swaya.me/frontend/public/assets/help-screens"
EMAIL = "demo@swaya.me"
PASSWORD = "Demo1234"

opts = webdriver.ChromeOptions()
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1280,900")
driver = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=opts)
wait = WebDriverWait(driver, 15)

def snap(name, delay=2):
    time.sleep(delay)
    p = os.path.join(OUT, f"{name}.png")
    driver.save_screenshot(p)
    print(f"  ✓ {name}.png ({os.path.getsize(p)//1024}KB)")

def login():
    driver.get(f"{BASE_URL}/login")
    time.sleep(2)
    inputs = [i for i in driver.find_elements(By.CSS_SELECTOR, "input") if i.is_displayed() and i.is_enabled()]
    inputs[0].send_keys(EMAIL)
    [i for i in inputs if i.get_attribute('type') == 'password'][0].send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))
    time.sleep(2)
    print("  ✓ logged in")

try:
    login()

    # Dashboard — shows both "New Quiz" and "Create Poll" buttons
    print("Dashboard with both buttons...")
    driver.get(f"{BASE_URL}/dashboard")
    time.sleep(3)
    snap("dashboard_buttons", delay=1)

    # Quiz builder (quiz mode) — fresh, shows correct answer field
    print("Quiz builder — quiz mode...")
    driver.get(f"{BASE_URL}/quiz/new")
    time.sleep(3)
    snap("quiz_builder_quiz_mode", delay=1)
    # Click Add Question to show the form
    try:
        btns = [b for b in driver.find_elements(By.XPATH, "//button[contains(., 'Add Question') or contains(., 'Add question')]") if b.is_displayed()]
        if btns:
            btns[0].click()
            time.sleep(2)
            snap("quiz_builder_quiz_question_form", delay=1)
            # Close the form
            close = driver.find_elements(By.XPATH, "//button[contains(., 'Cancel')]")
            if close: close[0].click()
    except Exception as e:
        print(f"  (add q: {e})")

    # Poll builder — shows all question types, no correct answer
    print("Poll builder — poll mode...")
    driver.get(f"{BASE_URL}/quiz/new?type=poll")
    time.sleep(3)
    snap("poll_builder_empty", delay=1)
    # Click Add Question
    try:
        btns = [b for b in driver.find_elements(By.XPATH, "//button[contains(., 'Add Question') or contains(., 'Add question')]") if b.is_displayed()]
        if btns:
            btns[0].click()
            time.sleep(2)
            snap("poll_builder_question_form", delay=1)
            # Close
            close = driver.find_elements(By.XPATH, "//button[contains(., 'Cancel')]")
            if close: close[0].click()
    except Exception as e:
        print(f"  (add q poll: {e})")

    # Existing quiz with questions — showing the correct answer marker
    print("Existing quiz editor (with questions)...")
    driver.get(f"{BASE_URL}/quiz/66/edit")
    time.sleep(3)
    snap("quiz_editor_with_questions", delay=1)

    # Also take dashboard screenshot showing quiz list with Quiz/Poll tags
    print("Dashboard quiz list...")
    driver.get(f"{BASE_URL}/dashboard")
    time.sleep(3)
    # Scroll down to quiz list
    driver.execute_script("window.scrollBy(0, 300)")
    time.sleep(1)
    snap("dashboard_quiz_list", delay=1)

    print("\nDone!")

except Exception as e:
    import traceback; traceback.print_exc()
    driver.save_screenshot(os.path.join(OUT, "_error_qvp.png"))
finally:
    driver.quit()

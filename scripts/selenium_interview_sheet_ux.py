"""
Selenium UX test for the Interview Sheet feature.
Targets test.swaya.me/quiz/1081/exam-results.

Run from repo root:
    sudo docker exec selenium-arm python3 /scripts/selenium_interview_sheet_ux.py

Or directly on the host (if selenium is installed):
    python3 scripts/selenium_interview_sheet_ux.py

Watch live at: http://www.swaya.me:7900 (noVNC — no password)
"""
import subprocess
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.common.exceptions import TimeoutException

# ── Config ────────────────────────────────────────────────────────────────────
WEBDRIVER_URL = 'http://localhost:4444'
TARGET_BASE = 'https://test.swaya.me'
QUIZ_ID = 1081
RESULTS_URL = f'{TARGET_BASE}/quiz/{QUIZ_ID}/exam-results'
COOKIE_DOMAIN = 'test.swaya.me'
TOKEN_SCRIPT = '/home/vinay/Swaya.me/scripts/generate_selenium_token.py'
PYTHON = '/home/vinay/Swaya.me/backend/.venv/bin/python3'

PASS = '\033[92m PASS\033[0m'
FAIL = '\033[91m FAIL\033[0m'
INFO = '\033[94m INFO\033[0m'

issues = []


def check(name, condition):
    if condition:
        print(f'{PASS} {name}')
    else:
        print(f'{FAIL} {name}')
        issues.append(name)
    return condition


def wait_for(driver, by, value, timeout=15, visible=True):
    try:
        cond = EC.visibility_of_element_located((by, value)) if visible else EC.presence_of_element_located((by, value))
        return WebDriverWait(driver, timeout).until(cond)
    except TimeoutException:
        return None


def main():
    # ── 1. Get JWT (from env or generate locally) ──────────────────────────────
    import os
    token = os.environ.get('SWAYA_TOKEN', '').strip()
    if token:
        print(f'{PASS} Token from environment ({token[:30]}...)')
    else:
        print(f'{INFO} Generating JWT token...')
        try:
            token = subprocess.check_output([PYTHON, TOKEN_SCRIPT]).decode().strip()
        except Exception as e:
            print(f'{FAIL} Token generation failed: {e}')
            sys.exit(1)
        print(f'{PASS} Token generated ({token[:30]}...)')

    # ── 2. Start Selenium ──────────────────────────────────────────────────────
    print(f'{INFO} Connecting to WebDriver at {WEBDRIVER_URL}...')
    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1440,900')
    options.add_experimental_option('prefs', {'download.default_directory': '/tmp'})
    driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=options)
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, 20)

    try:
        # ── 3. Inject cookie ───────────────────────────────────────────────────
        driver.get(TARGET_BASE)
        driver.add_cookie({
            'name': 'access_token',
            'value': token,
            'domain': COOKIE_DOMAIN,
            'path': '/',
            'secure': True,
            'httpOnly': True,
        })
        print(f'{PASS} Cookie injected')

        # ── 4. Navigate to exam results ─────────────────────────────────────────
        print(f'{INFO} Navigating to {RESULTS_URL}...')
        driver.get(RESULTS_URL)
        time.sleep(4)

        # ── 5. Assert Interview Sheet column visible ────────────────────────────
        page_text = driver.page_source
        check('Interview Sheet column header visible', 'Interview Sheet' in page_text)

        # ── 6. Assert completed participant shows active button ─────────────────
        # Find the first Interview Sheet button that is not disabled
        buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Interview Sheet')]")
        active_buttons = [b for b in buttons if b.is_enabled() and not b.get_attribute('disabled')]
        check('Active Interview Sheet button visible', len(active_buttons) > 0)

        if not active_buttons:
            print(f'{FAIL} No active buttons found — cannot continue UX test')
            return

        # ── 7. Click first active Interview Sheet button ────────────────────────
        first_btn = active_buttons[0]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", first_btn)
        print(f'{INFO} Clicked Interview Sheet button for participant 1')

        # ── 8. Assert modal opens with Generate button ──────────────────────────
        time.sleep(1.5)
        modal_title = wait_for(driver, By.XPATH, "//*[contains(@class,'ant-modal-title')]", timeout=6)
        check('Modal opened', modal_title is not None)

        generate_btn = wait_for(driver, By.XPATH, "//button[contains(., 'Generate Interview Sheet')]", timeout=5)
        check('Generate button visible in modal', generate_btn is not None)

        # ── 9. Click Generate ───────────────────────────────────────────────────
        if generate_btn:
            generate_btn.click()
            print(f'{INFO} Clicked Generate — waiting for AI response (up to 45s)...')

            # ── 10. Assert spinner appears ──────────────────────────────────────
            spinner = wait_for(driver, By.CLASS_NAME, 'ant-spin-spinning', timeout=5)
            check('Spinner appeared after clicking Generate', spinner is not None)

            # ── 11. Wait for content ────────────────────────────────────────────
            content_appeared = False
            for _ in range(45):
                time.sleep(1)
                page_src = driver.page_source
                if 'Regenerate' in page_src and 'Part' in page_src:
                    content_appeared = True
                    break
            check('Sheet content appeared (within 45s)', content_appeared)

            # ── 12. Assert rendered markdown (no raw **) ────────────────────────
            modal_body = driver.find_elements(By.CLASS_NAME, 'ai-analysis-content')
            raw_visible = False
            if modal_body:
                text = modal_body[0].text
                raw_visible = '**' in text or '##' in text
            check('Markdown rendered (no raw ** or ## symbols)', not raw_visible)

            # ── 13. Assert counter shows N/5 ───────────────────────────────────
            page_src = driver.page_source
            check('"1/5 used" counter visible', '1/5 used' in page_src)

            # ── 14. Assert Part A heading ───────────────────────────────────────
            check('Part A heading visible', 'part a' in page_src.lower())

            # ── 15. Assert email input prefilled ───────────────────────────────
            email_input = driver.find_elements(By.XPATH, "//input[@placeholder='Recipient email']")
            check('Email input present', len(email_input) > 0)

            # ── 16. Assert download buttons present ─────────────────────────────
            check('PDF download button visible', 'PDF' in page_src)
            check('Markdown download button visible', 'Markdown' in page_src)
            check('Word download button visible', 'Word' in page_src)

            # ── 17. Try PDF download ────────────────────────────────────────────
            pdf_btn = driver.find_elements(By.XPATH, "//button[contains(., 'PDF') and not(contains(.,'AI'))]")
            if pdf_btn:
                pdf_btn[-1].click()
                time.sleep(3)
                print(f'{PASS} PDF download button clicked')
            else:
                print(f'{FAIL} PDF button not found')
                issues.append('PDF button not found')

            # ── 18. Click Regenerate ─────────────────────────────────────────────
            regen_btn = driver.find_elements(By.XPATH, "//button[contains(., 'Regenerate')]")
            if regen_btn and regen_btn[0].is_enabled():
                regen_btn[0].click()
                print(f'{INFO} Clicked Regenerate — waiting...')
                time.sleep(45)
                page_src = driver.page_source
                check('Counter updates to 2/5 after regenerate', '2/5 used' in page_src)
            else:
                print(f'{INFO} Regenerate button disabled or not found (skipping)')

        # ── 19. Close modal ──────────────────────────────────────────────────────
        close_btn = driver.find_elements(By.CLASS_NAME, 'ant-modal-close')
        if close_btn:
            close_btn[0].click()
            time.sleep(1)
            modal_gone = wait_for(driver, By.XPATH, "//*[contains(@class,'ant-modal-title')]", timeout=3)
            check('Modal closes cleanly', modal_gone is None)

        # ── 20. Summary ──────────────────────────────────────────────────────────
        print()
        if not issues:
            print('\033[92m=== ALL CHECKS PASSED ===\033[0m')
        else:
            print(f'\033[91m=== {len(issues)} ISSUE(S) FOUND ===\033[0m')
            for issue in issues:
                print(f'  - {issue}')

    finally:
        driver.quit()


if __name__ == '__main__':
    main()

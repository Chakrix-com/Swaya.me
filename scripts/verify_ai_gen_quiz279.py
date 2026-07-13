"""
Verify fix: on a published (status=ready) non-exam quiz, the "Generate with AI"
and "Add Question" controls must be hidden/locked, since the backend rejects
adding questions to any non-DRAFT quiz. Bug: quiz.jsx only locked this for
exams (isExam && ready), not quizzes/polls in general.

Run:
    sudo docker exec selenium-arm python3 /scripts/verify_ai_gen_quiz279.py

Watch live at: http://www.swaya.me:7900 (noVNC — no password)
"""
import subprocess
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

sys.path.insert(0, '/home/vinay/Swaya.me/scripts')
from selenium_utils import inject_error_collectors, collect_js_errors  # noqa: E402

WEBDRIVER_URL = 'http://localhost:4444'
TARGET_BASE = 'https://test.swaya.me'
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


def main():
    import os
    token = os.environ.get('SWAYA_TOKEN', '').strip()
    if not token:
        token = subprocess.check_output([PYTHON, TOKEN_SCRIPT]).decode().strip()
    print(f'{PASS} Token ready ({token[:30]}...)')

    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1440,900')
    driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=options)
    driver.set_page_load_timeout(30)

    try:
        driver.get(TARGET_BASE)
        driver.add_cookie({
            'name': 'access_token', 'value': token, 'domain': COOKIE_DOMAIN,
            'path': '/', 'secure': True, 'httpOnly': True,
        })
        print(f'{PASS} Cookie injected for {COOKIE_DOMAIN}')

        driver.get(f'{TARGET_BASE}/quiz/279/edit')
        time.sleep(4)
        inject_error_collectors(driver)

        # Confirm the quiz actually loaded
        body_text = driver.find_element(By.TAG_NAME, 'body').text
        check('Quiz 279 edit page loaded (no crash screen)', 'edit' not in driver.current_url.lower() or 'error' not in body_text.lower()[:200])

        ai_buttons = driver.find_elements(By.XPATH, "//button[.//span[contains(text(),'Generate with AI')] or contains(., 'Generate with AI')]")
        visible_ai_buttons = [b for b in ai_buttons if b.is_displayed()]
        check(f'"Generate with AI" button is HIDDEN on published quiz (found {len(visible_ai_buttons)} visible)', len(visible_ai_buttons) == 0)

        add_q_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Add Question')]")
        visible_add_buttons = [b for b in add_q_buttons if b.is_displayed()]
        check(f'"Add Question" button is HIDDEN on published quiz (found {len(visible_add_buttons)} visible)', len(visible_add_buttons) == 0)

        locked_notice = driver.find_elements(By.XPATH, "//*[contains(text(),\"Unpublish Quiz\") or contains(text(),'unpublish')]")
        check('A locked/unpublish notice or button is present instead', len(locked_notice) > 0)

        screenshot_path = '/tmp/quiz279_verify.png'
        driver.save_screenshot(screenshot_path)
        print(f'{INFO} Screenshot saved to {screenshot_path}')

        collect_js_errors(driver, 'quiz279-edit')

        print(f'\n{"="*60}')
        if issues:
            print(f'{FAIL} {len(issues)} issue(s): {issues}')
            sys.exit(1)
        else:
            print(f'{PASS} All checks passed')
    finally:
        driver.quit()


if __name__ == '__main__':
    main()

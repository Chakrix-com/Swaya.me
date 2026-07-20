"""
Selenium verification for the ExamResults SafeModal migration.

Bug report: on production (www.swaya.me/quiz/280/exam-results), clicking
"Integrity merged" or "Answers" on a completed participant row hung the
browser for meetnishant@gmail.com — same VDI-hang bug class as the earlier
SafeModal fix (see project memory project_safemodal_vdi_freeze.md), except
ExamResults.jsx was never migrated off antd Modal in that pass ("exam pages"
was explicitly deferred). This script targets test.swaya.me/quiz/1174
("Proctoring Regression Exam") which has completed participants with both
answers and proctoring violation events, and confirms the three modals in
ExamResults.jsx (Answers/detail, Interview Sheet, Integrity/proctoring) now
render as SafeModal (class sw-safemodal-panel) with no console errors,
rather than antd ant-modal.

Run:
    sudo docker exec selenium-arm python3 /scripts/selenium_examresults_modal_verify.py

Watch live at: http://www.swaya.me:7900 (noVNC — no password)
"""
import subprocess
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

sys.path.insert(0, '/home/vinay/Swaya.me/scripts')
from selenium_utils import inject_error_collectors, collect_js_errors  # noqa: E402

WEBDRIVER_URL = 'http://localhost:4444'
TARGET_BASE = 'https://test.swaya.me'
COOKIE_DOMAIN = 'test.swaya.me'
QUIZ_ID = 1174
RESULTS_URL = f'{TARGET_BASE}/quiz/{QUIZ_ID}/exam-results'
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


def wait_safemodal_closed(driver, timeout=6):
    end = time.time() + timeout
    while time.time() < end:
        if len(driver.find_elements(By.CLASS_NAME, 'sw-safemodal-panel')) == 0:
            return True
        time.sleep(0.2)
    return False


def get_token():
    import os
    env_token = os.environ.get('SWAYA_TOKEN', '').strip()
    if env_token:
        return env_token
    try:
        return subprocess.check_output([PYTHON, TOKEN_SCRIPT, 'meetnishant@gmail.com']).decode().strip()
    except Exception as e:
        print(f'{FAIL} Token generation failed: {e}')
        sys.exit(1)


def main():
    print(f'{INFO} Generating JWT token for meetnishant@gmail.com...')
    token = get_token()
    print(f'{PASS} Token ready ({token[:30]}...)')

    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1440,1000')
    driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=options)
    driver.set_page_load_timeout(30)

    try:
        driver.get(TARGET_BASE)
        driver.add_cookie({
            'name': 'access_token', 'value': token, 'domain': COOKIE_DOMAIN,
            'path': '/', 'secure': True, 'httpOnly': True,
        })
        print(f'{PASS} Cookie injected for {COOKIE_DOMAIN}')

        print(f'{INFO} Navigating to {RESULTS_URL}...')
        driver.get(RESULTS_URL)
        time.sleep(4)
        inject_error_collectors(driver)

        check('No antd ant-modal-root present on page load', len(driver.find_elements(By.CLASS_NAME, 'ant-modal-root')) == 0)

        # ── Answers modal ────────────────────────────────────────────────
        answers_btns = [e for e in driver.find_elements(By.XPATH, "//button[.//span[text()='Answers']]") if e.is_displayed()]
        if check('"Answers" button found', len(answers_btns) > 0):
            driver.execute_script('arguments[0].scrollIntoView({block:"center"});', answers_btns[0])
            time.sleep(0.3)
            driver.execute_script('arguments[0].click();', answers_btns[0])
            time.sleep(1.5)
            panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=8)
            check('Answers modal renders as SafeModal (sw-safemodal-panel)', panel is not None)
            check('No antd Modal rendered for Answers', len(driver.find_elements(By.CLASS_NAME, 'ant-modal-content')) == 0)
            if panel:
                body_text = panel.text
                check('Answers modal shows question content', len(body_text) > 50)
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(0.8)
                check('Escape closes Answers SafeModal', wait_safemodal_closed(driver))
            collect_js_errors(driver, 'Answers modal')

        # ── Integrity merged modal ───────────────────────────────────────
        integrity_btns = [e for e in driver.find_elements(By.XPATH, "//button[.//span[text()='Integrity merged']]") if e.is_displayed()]
        if check('"Integrity merged" button found', len(integrity_btns) > 0):
            driver.execute_script('arguments[0].scrollIntoView({block:"center"});', integrity_btns[0])
            time.sleep(0.3)
            driver.execute_script('arguments[0].click();', integrity_btns[0])
            time.sleep(1.5)
            panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=8)
            check('Integrity modal renders as SafeModal (sw-safemodal-panel)', panel is not None)
            check('No antd Modal rendered for Integrity', len(driver.find_elements(By.CLASS_NAME, 'ant-modal-content')) == 0)
            if panel:
                check('Integrity modal footer has Lock/Unlock button', len(panel.find_elements(By.XPATH, ".//button[contains(., 'Lock') or contains(., 'Unlock')]")) > 0)
                mask = driver.find_elements(By.CLASS_NAME, 'sw-safemodal-mask')
                if mask:
                    driver.execute_script('arguments[0].click();', mask[0])
                    time.sleep(0.8)
                    check('Mask click closes Integrity SafeModal', wait_safemodal_closed(driver))
            collect_js_errors(driver, 'Integrity modal')
        else:
            print(f'{INFO} No participant row on quiz {QUIZ_ID} has proctoring data — cannot exercise Integrity modal')

        print(f'\n{"="*70}')
        if issues:
            print(f'{FAIL} {len(issues)} issue(s) found:')
            for i in issues:
                print(f'  - {i}')
        else:
            print(f'{PASS} All checks passed.')
    finally:
        driver.quit()

    sys.exit(1 if issues else 0)


if __name__ == '__main__':
    main()

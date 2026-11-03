"""
Selenium verification for the new Days/Hours/Minutes time-limit picker on the
coding-challenge Setup tab (SetupPanel.jsx DurationDHM), replacing the old
single "minutes" InputNumber.

Creates a throwaway coding-challenge quiz via API, opens its edit page,
screenshots the Setup tab's time-limit row, sets 3 days / 4 hours / 5 minutes
through the three fields, reloads, and confirms the value round-trips
(3d4h5m = 4565 minutes = 273900 seconds on the wire) before cleaning up.

Run:
    sudo docker exec selenium-arm python3 /scripts/selenium_duration_dhm_verify.py

Watch live at: http://www.swaya.me:7900 (noVNC — no password)
"""
import subprocess
import sys
import time

import requests
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
API = 'https://test.swaya.me/api/v1'
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


def get_token(email):
    args = [PYTHON, TOKEN_SCRIPT] + ([email] if email else [])
    try:
        return subprocess.check_output(args).decode().strip()
    except Exception as e:
        print(f'{FAIL} Token generation failed for {email}: {e}')
        sys.exit(1)


def main():
    token = get_token(None)
    headers = {'Authorization': f'Bearer {token}'}

    # /coding-challenges/default (not the generic /quizzes/ POST) is what
    # actually pre-provisions the Problem question this test needs to see
    # time_budget_seconds land on.
    quiz_res = requests.post(f'{API}/quizzes/coding-challenges/default', headers=headers)
    if quiz_res.status_code >= 300:
        print(f'{FAIL} Quiz creation failed: {quiz_res.status_code} {quiz_res.text}')
        sys.exit(1)
    quiz_id = quiz_res.json()['id']
    print(f'{INFO} Created quiz {quiz_id} ({quiz_res.json()["title"]})')

    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--window-size=1440,1000')
        driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=options)
        driver.get(TARGET_BASE)
        driver.add_cookie({'name': 'access_token', 'value': token, 'domain': COOKIE_DOMAIN, 'path': '/'})
        inject_error_collectors(driver)

        driver.get(f'{TARGET_BASE}/quiz/{quiz_id}/edit')

        duration_row = wait_for(driver, By.CLASS_NAME, 'sp-duration-dhm', timeout=20)
        check('Days/Hours/Minutes row rendered on Setup tab', duration_row is not None)

        inputs = driver.find_elements(By.CSS_SELECTOR, '.sp-duration-dhm input.ant-input-number-input')
        check('Exactly 3 number fields (days/hours/minutes)', len(inputs) == 3)

        addons = driver.find_elements(By.CSS_SELECTOR, '.sp-duration-dhm .ant-input-number-group-addon')
        addon_text = [a.text.strip() for a in addons]
        print(f'{INFO} Field unit labels: {addon_text}')
        check('Unit labels are d / h / min', addon_text == ['d', 'h', 'min'])

        driver.execute_script("window.scrollTo(0, arguments[0].getBoundingClientRect().top - 200)", duration_row)
        time.sleep(0.3)
        screenshot_path = '/tmp/claude-1005/-home-vinay-Swaya-me/fd28cf9b-9b63-48e8-a251-31ac8eb54576/scratchpad/duration_dhm_setup_tab.png'
        ok = driver.save_screenshot(screenshot_path)
        print(f'{INFO} Screenshot {"saved" if ok else "FAILED to save"}: {screenshot_path}')

        if len(inputs) == 3:
            days_input, hours_input, minutes_input = inputs
            for el, val in ((days_input, '3'), (hours_input, '4'), (minutes_input, '5')):
                el.click()
                driver.execute_script("arguments[0].select()", el)
                el.send_keys(val)
                time.sleep(0.2)
            # Tabbing between the three DHM fields keeps focus inside the Setup
            # panel's own container the whole time, so handleFormBlur's
            # `e.currentTarget.contains(e.relatedTarget)` guard never trips and
            # autosave never fires — true of any two fields in this form today,
            # not something the DHM picker changes. A real user triggers the
            # save by leaving the panel entirely; a programmatic .blur() (which
            # leaves relatedTarget null) reproduces that.
            driver.execute_script("document.activeElement && document.activeElement.blur()")

            time.sleep(1.0)  # debounce for autosave
            get_res = requests.get(f'{API}/quizzes/{quiz_id}', headers=headers)
            questions = get_res.json().get('questions', [])
            saved_seconds = questions[0]['time_budget_seconds'] if questions else None
            print(f'{INFO} Persisted time_budget_seconds after 3d 4h 5m entry: {saved_seconds}')
            # 3 days + 4 hours + 5 minutes = 4320 + 240 + 5 = 4565 minutes = 273900 seconds
            check('3d 4h 5m round-trips to 273900s server-side', saved_seconds == 273900)

        console_errors, failed_fetches = collect_js_errors(driver)
        check('No JS console errors', len(console_errors) == 0)
        check('No failed API calls', len(failed_fetches) == 0)
        if console_errors:
            print(f'{FAIL} JS errors: {console_errors}')
        if failed_fetches:
            print(f'{FAIL} Failed fetches: {failed_fetches}')

    finally:
        if driver:
            driver.quit()
        requests.delete(f'{API}/quizzes/{quiz_id}', headers=headers)
        print(f'{INFO} Cleaned up quiz {quiz_id}')

    print()
    if issues:
        print(f'{FAIL} {len(issues)} issue(s): {issues}')
        sys.exit(1)
    else:
        print(f'{PASS} All checks passed.')


if __name__ == '__main__':
    main()

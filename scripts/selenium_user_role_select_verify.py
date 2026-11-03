"""
Selenium verification that the User Management "Edit User" role dropdown
(frontend/src/features/admin/components/UserForm.jsx) is now a native
<select> and actually selectable, after replacing the antd Select that was
broken on the user's VDI (click-race in @rc-component/trigger).

Creates a throwaway user via API as 'viewer', edits it through the UI to
change role to 'user' using the native <select>, saves, and verifies via
API that the role actually persisted. Cleans up the throwaway user after.

Run:
    sudo docker exec selenium-arm python3 /scripts/selenium_user_role_select_verify.py

Watch live at: http://www.swaya.me:7900 (noVNC - no password)
"""
import subprocess
import sys
import time

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
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


def set_cookie(driver, token):
    driver.get(TARGET_BASE)
    driver.delete_all_cookies()
    driver.add_cookie({
        'name': 'access_token', 'value': token, 'domain': COOKIE_DOMAIN,
        'path': '/', 'secure': True, 'httpOnly': True,
    })


def main():
    token = get_token('meetnishant@gmail.com')
    headers = {'Authorization': f'Bearer {token}'}

    stamp = int(time.time())
    email = f'selenium.roletest.{stamp}@example.com'

    create_res = requests.post(f'{API}/users', json={
        'email': email,
        'password': 'TestPassword123!',
        'full_name': 'Selenium Role Test',
        'role': 'viewer',
        'is_active': True,
    }, headers=headers)
    if not check('Created throwaway user via API (role=viewer)', create_res.status_code in (200, 201)):
        print(create_res.text)
        sys.exit(1)
    user_id = create_res.json()['id']

    driver = None
    try:
        driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=webdriver.ChromeOptions())
        driver.set_window_size(1440, 900)
        set_cookie(driver, token)
        driver.get(f'{TARGET_BASE}/admin/users')
        time.sleep(3)
        inject_error_collectors(driver)

        rows = [r for r in driver.find_elements(By.XPATH, "//table//tr") if email in r.text]
        if not check('Throwaway user row visible in User Management', len(rows) > 0):
            sys.exit(1)
        row = rows[0]

        trigger_btns = row.find_elements(By.TAG_NAME, 'button')
        if not check('Row has "..." actions trigger', len(trigger_btns) > 0):
            sys.exit(1)
        driver.execute_script('arguments[0].click();', trigger_btns[-1])
        time.sleep(0.8)

        edit_items = [el for el in driver.find_elements(By.XPATH, "//*[contains(text(), 'Edit')]") if el.is_displayed()]
        if not check('"Edit" menu item found', len(edit_items) > 0):
            sys.exit(1)
        driver.execute_script('arguments[0].click();', edit_items[0])
        time.sleep(0.8)

        panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
        check('Edit User SafeModal opens', panel is not None)
        check('No antd ant-modal rendered', len(driver.find_elements(By.CLASS_NAME, 'ant-modal-content')) == 0)
        if not panel:
            sys.exit(1)

        native_selects = panel.find_elements(By.TAG_NAME, 'select')
        check('Role field is a native <select> (not antd Select)', len(native_selects) >= 1)
        check('No antd ant-select rendered in modal', len(panel.find_elements(By.CLASS_NAME, 'ant-select')) == 0)
        if not native_selects:
            sys.exit(1)

        role_select = Select(native_selects[0])
        current = role_select.first_selected_option.get_attribute('value')
        check('Role field initially shows "viewer"', current == 'viewer')

        role_select.select_by_value('user')
        time.sleep(0.3)
        check('Role field now shows "user" after selecting', Select(native_selects[0]).first_selected_option.get_attribute('value') == 'user')

        save_btns = [b for b in panel.find_elements(By.TAG_NAME, 'button') if b.text.strip().lower() in ('update', 'save')]
        check('Update button found', len(save_btns) > 0)
        if save_btns:
            driver.execute_script('arguments[0].click();', save_btns[0])
            time.sleep(1.5)

        errors, failed_fetches = collect_js_errors(driver)
        check('No JS console errors during flow', len(errors) == 0 and len(failed_fetches) == 0)

        verify_res = requests.get(f'{API}/users/{user_id}', headers=headers)
        role_now = verify_res.json().get('role') if verify_res.status_code == 200 else None
        check("Role persisted as 'user' via API after save", role_now == 'user')

    finally:
        requests.delete(f'{API}/users/{user_id}', headers=headers)
        print(f'{INFO} Cleaned up throwaway user {email}')
        if driver:
            driver.quit()

    print()
    if issues:
        print(f'{FAIL} {len(issues)} issue(s): {issues}')
        sys.exit(1)
    else:
        print(f'{PASS} All checks passed.')


if __name__ == '__main__':
    main()

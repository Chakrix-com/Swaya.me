"""
Selenium verification for the new Dashboard "Move to Folder" feature
(MoreActionsMenu item -> SafeModal with SafeTreeSelect -> PUT /quizzes/{id}/folder).

Creates a throwaway folder + quiz via API, drives the UI to move the quiz
into the folder, verifies success message + persisted folder_id, then
cleans up both.

Run:
    sudo docker exec selenium-arm python3 /scripts/selenium_move_to_folder_verify.py

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


def wait_gone(driver, class_name, timeout=6):
    end = time.time() + timeout
    while time.time() < end:
        if len(driver.find_elements(By.CLASS_NAME, class_name)) == 0:
            return True
        time.sleep(0.2)
    return False


def pick_clickable(driver, elements):
    """The folder name can also match the sidebar folder tree (behind the modal
    mask). Pick the element that's actually hit-testable at its own center —
    i.e. not obscured by another layer (mask, etc.)."""
    for el in elements:
        hit = driver.execute_script("""
            const el = arguments[0];
            const r = el.getBoundingClientRect();
            const x = r.left + r.width / 2, y = r.top + r.height / 2;
            const top = document.elementFromPoint(x, y);
            return top === el || el.contains(top) || (top && top.contains(el));
        """, el)
        if hit:
            return el
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
    folder_name = f'Selenium MoveFolder Test {stamp}'
    quiz_title = f'Selenium MoveFolder Quiz {stamp}'

    folder_res = requests.post(f'{API}/quizzes/folders', json={'name': folder_name}, headers=headers)
    if not check('Created throwaway folder via API', folder_res.status_code in (200, 201)):
        print(folder_res.text)
        sys.exit(1)
    folder_id = folder_res.json()['id']

    quiz_res = requests.post(f'{API}/quizzes/', json={'title': quiz_title, 'quiz_type': 'quiz'}, headers=headers)
    if not check('Created throwaway quiz via API', quiz_res.status_code in (200, 201)):
        print(quiz_res.text)
        sys.exit(1)
    quiz_id = quiz_res.json()['id']

    driver = None
    try:
        driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=webdriver.ChromeOptions())
        driver.set_window_size(1440, 900)
        set_cookie(driver, token)
        driver.get(f'{TARGET_BASE}/dashboard')
        time.sleep(3)
        inject_error_collectors(driver)

        # Find the throwaway quiz's row and open its "..." menu
        rows = [r for r in driver.find_elements(By.XPATH, "//table//tr") if quiz_title in r.text]
        if not check('Throwaway quiz row visible on dashboard', len(rows) > 0):
            sys.exit(1)
        row = rows[0]

        # MoreActionsMenu trigger is the last button in the actions cell (an ellipsis icon button)
        actions_cell_buttons = row.find_elements(By.TAG_NAME, 'button')
        if not check('Row has action buttons incl. "..." trigger', len(actions_cell_buttons) > 0):
            sys.exit(1)
        trigger = actions_cell_buttons[-1]
        driver.execute_script('arguments[0].click();', trigger)
        time.sleep(0.8)

        move_item = None
        for el in driver.find_elements(By.XPATH, "//*[contains(text(), 'Move to Folder')]"):
            if el.is_displayed():
                move_item = el
                break
        if not check('"Move to Folder" menu item found', move_item is not None):
            sys.exit(1)
        driver.execute_script('arguments[0].click();', move_item)
        time.sleep(0.8)

        panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
        check('Move-to-Folder SafeModal opens', panel is not None)
        check('No antd ant-modal rendered', len(driver.find_elements(By.CLASS_NAME, 'ant-modal-content')) == 0)
        if not panel:
            sys.exit(1)

        # Open the SafeTreeSelect and pick our throwaway folder
        tree_trigger = panel.find_element(By.XPATH, ".//div[@style[contains(., 'cursor: pointer')]][1]")
        driver.execute_script('arguments[0].click();', tree_trigger)
        time.sleep(0.5)
        # Dropdown is portaled to document.body (outside `panel`), not nested inside it.
        options = [e for e in driver.find_elements(By.XPATH, f"//*[contains(text(), '{folder_name}')]") if e.is_displayed()]
        check('Throwaway folder option appears in picker', len(options) > 0)
        target = pick_clickable(driver, options) if options else None
        check('Throwaway folder option is clickable (not obscured)', target is not None)
        if target:
            driver.execute_script('arguments[0].click();', target)
            time.sleep(0.3)
            check('Folder selected in picker (shown as value)', folder_name in panel.text)

        save_btns = [b for b in panel.find_elements(By.TAG_NAME, 'button') if b.text.strip() in ('Save', 'save')]
        check('Save button found', len(save_btns) > 0)
        if save_btns:
            driver.execute_script('arguments[0].click();', save_btns[0])
            time.sleep(1.5)

        check('Modal closed after save', wait_gone(driver, 'sw-safemodal-panel'))

        collect_js_errors(driver, 'Move to Folder')

    finally:
        # Verify persisted state via API regardless of UI outcome, then clean up
        verify_res = requests.get(f'{API}/quizzes/', headers=headers)
        moved_ok = False
        if verify_res.status_code == 200:
            match = next((q for q in verify_res.json() if q['id'] == quiz_id), None)
            moved_ok = bool(match and match.get('folder_id') == folder_id)
        check('quiz.folder_id persisted to the throwaway folder (API-verified)', moved_ok)

        requests.delete(f'{API}/quizzes/{quiz_id}', headers=headers)
        requests.delete(f'{API}/quizzes/folders/{folder_id}', headers=headers)
        print(f'{INFO} Cleaned up throwaway quiz {quiz_id} and folder {folder_id}')
        if driver:
            driver.quit()

    print(f'\n{"="*60}')
    if issues:
        print(f'{FAIL} {len(issues)} issue(s): {issues}')
        sys.exit(1)
    else:
        print(f'{PASS} All Move-to-Folder checks passed')


if __name__ == '__main__':
    main()

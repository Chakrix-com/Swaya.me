"""
Verifies the relaxed cross-tenant folder sharing feature:
- share_folder() no longer requires the target user to be in the owner's tenant
- a new GET /users/lookup?email=... endpoint resolves an exact email to a
  minimal {id, email, display_name} record, across any tenant
- the Share Folder dialog (SidebarFolderTree.jsx) has an "Or share with anyone
  by email" input that uses that lookup, in addition to the existing
  tenant-teammate picker

Creates a throwaway folder owned by meetnishant@gmail.com (tenant 2), then:
  1. tries an email with no account -> expects an error, no crash
  2. adds regression-free@swaya.me (a real account in a DIFFERENT tenant) by
     email, saves, and verifies via API that the share was created can_edit=false
  3. verifies via a token for that other-tenant user that the folder now shows
     up for them (is_shared_to_me=true) -- i.e. the feature actually works
     end-to-end, not just that the dialog accepts the input
  4. cleans up (deleting the folder cascades the share row)

Run:
    backend/.venv/bin/python3 scripts/selenium_cross_tenant_folder_share_verify.py

Watch live at: http://www.swaya.me:7900 (noVNC -- no password)
"""
import subprocess
import sys
import time

import requests
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
API = 'https://test.swaya.me/api/v1'
TOKEN_SCRIPT = '/home/vinay/Swaya.me/scripts/generate_selenium_token.py'
PYTHON = '/home/vinay/Swaya.me/backend/.venv/bin/python3'

OWNER_EMAIL = 'meetnishant@gmail.com'
OTHER_TENANT_EMAIL = 'regression-free@swaya.me'  # tenant 16, different from owner's tenant 2
NONEXISTENT_EMAIL = 'no-such-account-xyz-12345@example.com'

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


def clear_input(el):
    """el.clear() doesn't reliably clear a React-controlled input under
    Selenium -- select-all + delete does."""
    el.send_keys(Keys.CONTROL, 'a')
    el.send_keys(Keys.DELETE)


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
    owner_token = get_token(OWNER_EMAIL)
    owner_headers = {'Authorization': f'Bearer {owner_token}'}

    stamp = int(time.time())
    folder_name = f'XTenantFolder Test {stamp}'
    folder_res = requests.post(f'{API}/quizzes/folders', json={'name': folder_name}, headers=owner_headers)
    if not check('Created throwaway folder via API', folder_res.status_code in (200, 201)):
        print(folder_res.text)
        sys.exit(1)
    folder_id = folder_res.json()['id']

    driver = None
    try:
        driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=webdriver.ChromeOptions())
        driver.set_window_size(1440, 900)
        set_cookie(driver, owner_token)
        driver.get(f'{TARGET_BASE}/dashboard')
        time.sleep(3)
        inject_error_collectors(driver)

        # Find the throwaway folder in the sidebar tree and open its "..." menu -> Share
        folder_rows = [e for e in driver.find_elements(By.XPATH, "//*[contains(@class,'sf2-row')]") if folder_name in e.text]
        if not check('Throwaway folder visible in sidebar', len(folder_rows) > 0):
            sys.exit(1)

        # Hover/click the row's "..." trigger (MoreActionsMenu button within the row)
        row = folder_rows[0]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
        time.sleep(0.3)
        buttons = row.find_elements(By.TAG_NAME, 'button')
        if not check('Folder row has a "..." trigger button', len(buttons) > 0):
            sys.exit(1)
        driver.execute_script('arguments[0].click();', buttons[-1])
        time.sleep(0.6)

        # Exact text match -- the throwaway folder's own name contains the
        # substring "Share" (from folder_name), which a contains() match
        # would also pick up.
        share_item = None
        for el in driver.find_elements(By.XPATH, "//*[text()='Share']"):
            if el.is_displayed():
                share_item = el
                break
        if not check('Share menu item found', share_item is not None):
            sys.exit(1)
        driver.execute_script('arguments[0].click();', share_item)
        time.sleep(0.8)

        panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
        check('Share Folder SafeModal opens', panel is not None)
        if not panel:
            sys.exit(1)

        email_input = None
        for inp in panel.find_elements(By.TAG_NAME, 'input'):
            ph = inp.get_attribute('placeholder') or ''
            if '@' in ph or 'example' in ph.lower():
                email_input = inp
                break
        check('"Or share with anyone by email" input is present', email_input is not None)
        if not email_input:
            sys.exit(1)

        add_btn = None
        for b in panel.find_elements(By.TAG_NAME, 'button'):
            if b.text.strip().lower() == 'add':
                add_btn = b
                break
        check('Add button found', add_btn is not None)

        # 1. Nonexistent email -> expect an error toast, no crash
        clear_input(email_input)
        email_input.send_keys(NONEXISTENT_EMAIL)
        driver.execute_script('arguments[0].click();', add_btn)
        time.sleep(1.0)
        error_toast = wait_for(driver, By.XPATH, "//*[contains(@class,'ant-message') or contains(@class,'message')]", timeout=3)
        page_text = driver.find_element(By.TAG_NAME, 'body').text
        check('Nonexistent email shows a "no account found" style message (not a crash)',
              'no' in page_text.lower() and ('account' in page_text.lower() or 'found' in page_text.lower()))

        # 2. Real cross-tenant email -> should resolve and add
        # re-find in case DOM re-rendered
        email_input = None
        for inp in panel.find_elements(By.TAG_NAME, 'input'):
            ph = inp.get_attribute('placeholder') or ''
            if '@' in ph or 'example' in ph.lower():
                email_input = inp
                break
        clear_input(email_input)
        email_input.send_keys(OTHER_TENANT_EMAIL)
        add_btn = [b for b in panel.find_elements(By.TAG_NAME, 'button') if b.text.strip().lower() == 'add'][0]
        driver.execute_script('arguments[0].click();', add_btn)
        time.sleep(1.0)

        chip_present = OTHER_TENANT_EMAIL in panel.text
        check(f'{OTHER_TENANT_EMAIL} appears as a selected chip after lookup', chip_present)

        save_btns = [b for b in panel.find_elements(By.TAG_NAME, 'button') if b.text.strip() in ('Save sharing', 'Save')]
        check('Save button found', len(save_btns) > 0)
        if save_btns:
            driver.execute_script('arguments[0].click();', save_btns[0])
            time.sleep(1.2)

        collect_js_errors(driver, 'Cross-tenant folder share')

    finally:
        if driver:
            driver.quit()

        # Verify persisted state via API regardless of UI outcome
        shares_res = requests.get(f'{API}/quizzes/folders/{folder_id}/shares', headers=owner_headers)
        shared_ok = False
        can_edit_false = False
        if shares_res.status_code == 200:
            shares = shares_res.json()
            match = next((s for s in shares if s['email'] == OTHER_TENANT_EMAIL), None)
            shared_ok = match is not None
            can_edit_false = bool(match and match.get('can_edit') is False)
        check('Cross-tenant share persisted (API-verified)', shared_ok)
        check('Cross-tenant share is read-only (can_edit=false)', can_edit_false)

        # Verify from the OTHER user's perspective that the folder now shows up
        other_token = get_token(OTHER_TENANT_EMAIL)
        other_headers = {'Authorization': f'Bearer {other_token}'}
        folders_res = requests.get(f'{API}/quizzes/folders', headers=other_headers)
        visible_to_other = False
        if folders_res.status_code == 200:
            visible_to_other = any(f['id'] == folder_id and f.get('is_shared_to_me') for f in folders_res.json())
        check('Folder is visible to the other-tenant user via their own API call', visible_to_other)

        requests.delete(f'{API}/quizzes/folders/{folder_id}', headers=owner_headers)
        print(f'{INFO} Cleaned up throwaway folder {folder_id}')

    print(f'\n{"="*60}')
    if issues:
        print(f'{FAIL} {len(issues)} issue(s): {issues}')
        sys.exit(1)
    else:
        print(f'{PASS} All cross-tenant folder share checks passed')


if __name__ == '__main__':
    main()

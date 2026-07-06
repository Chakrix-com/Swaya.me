"""
Selenium repro/verify for the cross-account stale-folder bug on test.swaya.me.

Bug: Redux store was never reset on logout, so a subsequent login (same tab,
no full page reload) inherited the previous account's `quiz.folders` because
SidebarFolderTree's fetch-guard skips re-fetching when `folders.length > 0`.

Repro sequence (must be a REAL logout + REAL login form submit, in the same
browser tab, no driver.get() in between the two — a fresh navigation would
mask the bug by resetting the JS process):
  1. Log in as meetnishant@gmail.com (has folders: Old quizzes, Level 2, Ruchi-Tests)
  2. Confirm those folders show in the sidebar
  3. Click profile avatar -> Sign Out (real UI action, dispatches logout())
  4. Fill real login form for demo@swaya.me / Demo1234, submit
  5. Confirm the sidebar no longer shows meetnishant's folders

Run:
    /home/vinay/Swaya.me/backend/.venv/bin/python3 scripts/selenium_folder_leak_verify.py
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
TOKEN_SCRIPT = '/home/vinay/Swaya.me/backend/.venv/bin/python3'
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


def sidebar_folder_names(driver):
    els = driver.find_elements(By.CSS_SELECTOR, '.sf2-label')
    return [e.text for e in els]


def main():
    token = subprocess.check_output(
        [PYTHON, '/home/vinay/Swaya.me/scripts/generate_selenium_token.py', 'tmp.folder.verify@gmail.com']
    ).decode().strip()
    print(f'{PASS} Token generated for tmp.folder.verify@gmail.com (tenant 30)')

    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1440,900')
    driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=options)
    driver.set_page_load_timeout(30)

    try:
        # ── 1. Log in as meetnishant via cookie ────────────────────────────
        driver.get(TARGET_BASE)
        driver.add_cookie({
            'name': 'access_token', 'value': token, 'domain': COOKIE_DOMAIN,
            'path': '/', 'secure': True, 'httpOnly': True,
        })
        driver.get(f'{TARGET_BASE}/dashboard')
        time.sleep(3)
        inject_error_collectors(driver)

        names_before = sidebar_folder_names(driver)
        print(f'{INFO} temp-tenant sidebar folders: {names_before}')
        check('temp tenant folder visible before switch', 'Leaky Tenant Folder' in names_before)

        # ── 2. Real Sign Out via profile menu (dispatches logout()) ────────
        avatar = driver.find_element(By.CSS_SELECTOR, '.ant-pro-global-header-header-actions-avatar')
        avatar.click()
        time.sleep(0.5)

        signout = None
        for el in driver.find_elements(By.XPATH, "//*[contains(text(),'Sign out')]"):
            signout = el
            break
        if not check('Found Sign Out menu item', signout is not None):
            return
        driver.execute_script("arguments[0].click();", signout)
        time.sleep(2)

        check('No longer authenticated after sign out (left /dashboard)', '/dashboard' not in driver.current_url)
        check('No infinite loading spinner after sign out', len(driver.find_elements(By.CLASS_NAME, 'anticon-loading')) == 0)

        # Signed-out users may land on /login directly or the marketing
        # homepage (/) depending on the route — click through to the real
        # login form either way (soft nav, matches real user behavior).
        if '/login' not in driver.current_url:
            login_link = wait_for(driver, By.XPATH, "//a[contains(text(),'Login')] | //button[contains(text(),'Login')]", timeout=10)
            if login_link:
                driver.execute_script("arguments[0].click();", login_link)
                time.sleep(2)

        # ── 3. Real login as demo@swaya.me via the actual form ──────────────
        email_input = wait_for(driver, By.CSS_SELECTOR, "#login_email", timeout=15)
        if not check('Login email field present', email_input is not None):
            return
        password_input = wait_for(driver, By.CSS_SELECTOR, "#login_password", timeout=15)
        if not check('Login password field present', password_input is not None):
            return
        email_input.clear()
        email_input.send_keys('demo@swaya.me')
        password_input.clear()
        password_input.send_keys('Demo1234')
        submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", submit)
        time.sleep(3)

        check('Logged in as demo (left /login)', '/login' not in driver.current_url)

        # ── 4. Confirm the temp tenant's folder is NOT visible to demo, and
        #      that demo's own real folders loaded correctly (proving a
        #      fresh fetch happened, not just an empty/stuck list) ─────────
        names_after = sidebar_folder_names(driver)
        print(f'{INFO} demo sidebar folders (same-tab switch, no reload): {names_after}')
        check('Temp tenant folder NOT leaked into demo session', 'Leaky Tenant Folder' not in names_after)
        check("Demo's own real folders loaded fresh", 'Old quizzes' in names_after and 'Level 2' in names_after)

        collect_js_errors(driver, 'account-switch')

        print(f'\n{"="*60}')
        if issues:
            print(f'{FAIL} {len(issues)} issue(s): {issues}')
        else:
            print(f'{PASS} All checks passed — fix confirmed')
    finally:
        driver.quit()


if __name__ == '__main__':
    main()

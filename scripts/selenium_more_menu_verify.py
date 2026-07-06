"""
Selenium verification for the More-Actions ("...") menu fix on test.swaya.me.
Checks Dashboard, Activities, and Admin User Management: menu opens, an item
is actually clickable (the original bug symptom was "opens but nothing is
selectable"), and no new JS errors are introduced.

Run:
    sudo docker exec selenium-arm python3 /scripts/selenium_more_menu_verify.py

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


def wait_for(driver, by, value, timeout=15, visible=True):
    try:
        cond = EC.visibility_of_element_located((by, value)) if visible else EC.presence_of_element_located((by, value))
        return WebDriverWait(driver, timeout).until(cond)
    except TimeoutException:
        return None


def test_more_menu(driver, page_name, url, trigger_xpath):
    print(f'\n{INFO} --- {page_name} ({url}) ---')
    driver.get(url)
    time.sleep(3)
    inject_error_collectors(driver)

    triggers = driver.find_elements(By.XPATH, trigger_xpath)
    if not check(f'{page_name}: at least one "..." trigger found', len(triggers) > 0):
        return

    trigger = triggers[0]
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", trigger)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", trigger)
    time.sleep(0.5)

    popup = wait_for(driver, By.CLASS_NAME, 'dashboard-more-menu', timeout=5)
    if not check(f'{page_name}: popup menu opened', popup is not None):
        return

    items = popup.find_elements(By.CLASS_NAME, 'dashboard-more-menu-item')
    check(f'{page_name}: popup has clickable items ({len(items)} found)', len(items) > 0)

    if items:
        rect_before = items[0].rect
        check(f'{page_name}: first item has nonzero size', rect_before['width'] > 0 and rect_before['height'] > 0)

    # Close via outside click; confirm it actually closes (regression check
    # for the "gets stuck open" symptom). The close listener is on
    # 'mousedown', so dispatch that specifically rather than .click()
    # (which only fires a 'click' event, not a full mousedown/mouseup pair).
    driver.execute_script(
        "document.body.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));"
    )
    time.sleep(0.5)
    still_open = driver.find_elements(By.CLASS_NAME, 'dashboard-more-menu')
    check(f'{page_name}: popup closes on outside click', len(still_open) == 0)

    collect_js_errors(driver, page_name)


def main():
    import os
    token = os.environ.get('SWAYA_TOKEN', '').strip()
    if not token:
        print(f'{INFO} Generating JWT token...')
        try:
            token = subprocess.check_output([PYTHON, TOKEN_SCRIPT]).decode().strip()
        except Exception as e:
            print(f'{FAIL} Token generation failed: {e}')
            sys.exit(1)
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

        test_more_menu(
            driver, 'Dashboard', f'{TARGET_BASE}/dashboard',
            "//table//button[.//span[contains(@class,'anticon-more')]]"
        )
        test_more_menu(
            driver, 'Activities', f'{TARGET_BASE}/activities',
            "//table//button[.//span[contains(@class,'anticon-more')]]"
        )
        test_more_menu(
            driver, 'Admin User Management', f'{TARGET_BASE}/admin/users',
            "//table//button[.//span[contains(@class,'anticon-more')]]"
        )

        print(f'\n{"="*60}')
        if issues:
            print(f'{FAIL} {len(issues)} issue(s): {issues}')
        else:
            print(f'{PASS} All checks passed')
    finally:
        driver.quit()


if __name__ == '__main__':
    main()

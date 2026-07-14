"""
Selenium verification for SafeMultiSelect replacing antd Select in the
folder "Share" modal (SidebarFolderTree.jsx) on test.swaya.me.

Run:
    sudo docker exec selenium-arm python3 /scripts/selenium_safe_multiselect_verify.py

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


def main():
    import os
    token = os.environ.get('SWAYA_TOKEN', '').strip()
    if not token:
        print(f'{INFO} Generating JWT token...')
        try:
            token = subprocess.check_output([PYTHON, TOKEN_SCRIPT, 'meetnishant@gmail.com']).decode().strip()
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

        driver.get(f'{TARGET_BASE}/dashboard')
        time.sleep(3)
        inject_error_collectors(driver)

        # Find a folder row's "..." trigger in the sidebar tree
        triggers = driver.find_elements(By.XPATH, "//*[contains(@class,'sf2')]//button[.//span[contains(@class,'anticon-more')]]")
        if not check('Sidebar: at least one folder "..." trigger found', len(triggers) > 0):
            driver.save_screenshot('/tmp/safe_multiselect_no_trigger.png')
            return

        trigger = triggers[0]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", trigger)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", trigger)
        time.sleep(0.5)

        # Click "Share" item in the folder menu
        share_items = driver.find_elements(By.XPATH, "//*[contains(text(),'Share')]")
        share_item = None
        for el in share_items:
            if el.is_displayed():
                share_item = el
                break
        if not check('Folder menu: "Share" item found and visible', share_item is not None):
            driver.save_screenshot('/tmp/safe_multiselect_no_share.png')
            return

        driver.execute_script("arguments[0].click();", share_item)
        time.sleep(1)

        modal = wait_for(driver, By.CLASS_NAME, 'ant-modal-content', timeout=5)
        check('Share modal opened', modal is not None)

        # The SafeMultiSelect input box
        ms_input = wait_for(driver, By.XPATH, "//div[contains(@class,'ant-modal-content')]//input[@placeholder]", timeout=5)
        if not check('SafeMultiSelect input found', ms_input is not None):
            driver.save_screenshot('/tmp/safe_multiselect_no_input.png')
            return

        driver.execute_script("arguments[0].click();", ms_input)
        time.sleep(0.5)

        # Dropdown panel should appear with checkbox options (or notFoundContent)
        panel_visible = len(driver.find_elements(By.CLASS_NAME, 'sw-multiselect-panel')) > 0
        check('SafeMultiSelect dropdown panel opened on click', panel_visible)

        checkboxes = driver.find_elements(By.XPATH, "//div[contains(@class,'ant-modal-content')]//input[@type='checkbox']")
        print(f'{INFO} {len(checkboxes)} selectable teammate option(s) found')

        if checkboxes:
            cb = checkboxes[0]
            driver.execute_script("arguments[0].closest('div[style*=\"cursor: pointer\"]').click();", cb)
            time.sleep(0.5)
            # A chip (selected tag) should now render inside the input box
            chips = driver.find_elements(By.CLASS_NAME, 'sw-multiselect-chip')
            chip_count_before = len(chips)
            check('Selecting an option renders a chip', chip_count_before > 0)

            # Panel should remain open after a selection (matches antd multi-select UX)
            panel_still_open = len(driver.find_elements(By.CLASS_NAME, 'sw-multiselect-panel')) > 0
            check('Dropdown panel stays open after selecting an item', panel_still_open)

            # Remove the first chip via its own close icon
            if chips:
                close_icon = chips[0].find_element(By.CLASS_NAME, 'sw-multiselect-chip-remove')
                driver.execute_script("arguments[0].click();", close_icon)
                time.sleep(0.3)
                chip_count_after = len(driver.find_elements(By.CLASS_NAME, 'sw-multiselect-chip'))
                check('Removing chip via its "x" works', chip_count_after == chip_count_before - 1)

        # Outside click (on modal title) should close the multiselect panel, not the whole modal
        title = driver.find_element(By.CLASS_NAME, 'ant-modal-header')
        driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));", title)
        time.sleep(0.5)
        panel_after_outside_click = len(driver.find_elements(By.CLASS_NAME, 'sw-multiselect-panel')) > 0
        check('Dropdown panel closes on outside click (modal itself stays open)', not panel_after_outside_click)
        modal_still_present = len(driver.find_elements(By.CLASS_NAME, 'ant-modal-content')) > 0
        check('Modal remains open (not accidentally dismissed)', modal_still_present)

        driver.save_screenshot('/tmp/safe_multiselect_final.png')
        collect_js_errors(driver, 'Share modal / SafeMultiSelect')

    finally:
        driver.quit()

    print()
    if issues:
        print(f'{FAIL} {len(issues)} issue(s) found:')
        for i in issues:
            print(f'  - {i}')
        sys.exit(1)
    else:
        print(f'{PASS} All checks passed.')


if __name__ == '__main__':
    main()

"""
Selenium verification for SafeTreeSelect replacing antd TreeSelect in the
folder Create/Rename modals (SidebarFolderTree.jsx) on test.swaya.me.

Run with SWAYA_TOKEN env var already set (JWT generated on host, never
printed — passed straight into the container).
"""
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
    token = os.environ['SWAYA_TOKEN']

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
        driver.get(f'{TARGET_BASE}/dashboard')
        time.sleep(3)
        inject_error_collectors(driver)

        # Open a folder's "..." menu -> Rename
        triggers = driver.find_elements(By.XPATH, "//*[contains(@class,'sf2')]//button[.//span[contains(@class,'anticon-more')]]")
        if not check('Sidebar: at least one folder "..." trigger found', len(triggers) > 0):
            return
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", triggers[0])
        driver.execute_script("arguments[0].click();", triggers[0])
        time.sleep(0.5)

        rename_items = [e for e in driver.find_elements(By.XPATH, "//*[contains(text(),'Rename')]") if e.is_displayed()]
        if not check('Folder menu: "Rename" item found', len(rename_items) > 0):
            return
        driver.execute_script("arguments[0].click();", rename_items[0])
        time.sleep(1)

        modal = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
        check('Rename modal opened', modal is not None)

        name_input = wait_for(driver, By.XPATH, "//div[contains(@class,'sw-safemodal-body')]//input[not(@type='checkbox')]", timeout=5)
        check('Name input present and typeable', name_input is not None)
        if name_input:
            name_input.send_keys(' (edited)')

        # Open the SafeTreeSelect (Move To) picker
        picker = wait_for(driver, By.XPATH, "//div[contains(@class,'sw-safemodal-body')]//div[@style[contains(.,'cursor: pointer')]]", timeout=5)
        check('SafeTreeSelect picker box found', picker is not None)
        if picker:
            driver.execute_script("arguments[0].click();", picker)
            time.sleep(0.5)
            options_visible = len(driver.find_elements(By.XPATH, "//div[contains(@class,'sw-safemodal-body')]//div[contains(@style,'zIndex: 1050') or contains(@style,'z-index: 1050')]")) > 0
            check('SafeTreeSelect dropdown opened', options_visible)
            # close it again by clicking the picker box itself
            driver.execute_script("arguments[0].click();", picker)
            time.sleep(0.3)

        # Now the critical check: are Cancel/Save buttons in the modal footer clickable?
        cancel_btn = wait_for(driver, By.XPATH, "//div[contains(@class,'sw-safemodal-footer')]//button[.//span[text()='Cancel']]", timeout=5)
        check('Cancel button found in modal footer', cancel_btn is not None)
        if cancel_btn:
            rect = cancel_btn.rect
            check('Cancel button has nonzero size (not collapsed/hidden)', rect['width'] > 0 and rect['height'] > 0)
            driver.execute_script("arguments[0].click();", cancel_btn)
            time.sleep(0.5)
            # SafeModal (unlike antd Modal) does not stay mounted with
            # display:none when closed — it's a controlled `if (!open) return
            # null` component, so a closed SafeModal has zero DOM presence at
            # all. Absence of .sw-safemodal-panel is itself the closed signal.
            modal_closed = len(driver.find_elements(By.CLASS_NAME, 'sw-safemodal-panel')) == 0
            check('Clicking Cancel actually closes the modal (buttons are responsive)', modal_closed)
            page_interactive = driver.execute_script("""
                const el = document.elementFromPoint(50, 50);
                return el ? !el.closest('.sw-safemodal-mask') : true;
            """)
            check('Page remains interactive after closing (no zombie overlay)', page_interactive)

        driver.save_screenshot('/tmp/safe_treeselect_final.png')
        collect_js_errors(driver, 'Rename modal / SafeTreeSelect')

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

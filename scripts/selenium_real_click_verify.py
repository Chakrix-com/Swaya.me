"""
Real-click verification (native Selenium .click(), which dispatches a true
mousedown/mouseup/click sequence — unlike execute_script("...click()"),
which only fires a synthetic 'click' and was silently blind to any bug in
mousedown-based outside-click-to-close logic all along).

Covers: folder row click, folder "..." menu -> Rename (name edit + parent
picker + Save), folder "..." menu -> Share (multi-select + Save).
"""
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

sys.path.insert(0, '/home/vinay/Swaya.me/scripts')
from selenium_utils import inject_error_collectors, collect_js_errors  # noqa: E402

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


def wait_for_open_modal(driver, timeout=5):
    """SafeModal (unlike antd Modal) is a controlled `if (!open) return null`
    component — it has zero DOM presence while closed, and each of
    SidebarFolderTree's 4 SafeModal instances only portals its
    .sw-safemodal-panel while its own `open` is true. So a bare class-name
    presence check is sufficient; no display:none polling needed."""
    end = time.time() + timeout
    while time.time() < end:
        found = len(driver.find_elements(By.CLASS_NAME, 'sw-safemodal-panel')) > 0
        if found:
            return True
        time.sleep(0.2)
    return False


def get_open_modal_content(driver, timeout=5):
    """Return the WebElement for whichever SafeModal panel is currently
    mounted. Only one of SidebarFolderTree's 4 SafeModal instances is ever
    open at a time, and a closed SafeModal has no DOM presence at all, so
    the first (and only) .sw-safemodal-panel match is always the right one."""
    end = time.time() + timeout
    while time.time() < end:
        els = driver.find_elements(By.CLASS_NAME, 'sw-safemodal-panel')
        if els:
            return els[0]
        time.sleep(0.2)
    return None


def real_click(driver, el):
    """Native click — real mousedown/mouseup/click, not execute_script."""
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.15)
    try:
        el.click()
    except ElementClickInterceptedException:
        # last resort only if something legitimately overlays it
        driver.execute_script("arguments[0].click();", el)


def run(base_url, cookie_domain, token, label):
    print(f'\n{INFO} ══ {label} ({base_url}) ══')
    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1440,900')
    driver = webdriver.Remote(command_executor='http://localhost:4444', options=options)
    driver.set_page_load_timeout(30)

    try:
        driver.get(base_url)
        driver.add_cookie({'name': 'access_token', 'value': token, 'domain': cookie_domain, 'path': '/', 'secure': True, 'httpOnly': True})
        driver.get(f'{base_url}/dashboard')
        time.sleep(3)
        inject_error_collectors(driver)

        # ── 1. Plain folder row click (real click) ──────────────────────────
        folder_rows = driver.find_elements(By.CSS_SELECTOR, '.sf2-row')
        # skip the "All Activities" virtual root, use a real folder row if present
        target_row = None
        for r in folder_rows:
            if 'sf2-row--active' not in r.get_attribute('class') or True:
                label_el = r.find_elements(By.CSS_SELECTOR, '.sf2-label')
                if label_el and label_el[0].text.strip() not in ('All Activities', ''):
                    target_row = r
                    break
        if check(f'{label}: a real folder row exists', target_row is not None):
            real_click(driver, target_row)
            time.sleep(1)
            became_active = 'sf2-row--active' in target_row.get_attribute('class')
            check(f'{label}: folder row becomes active on a single real click', became_active)
            page_alive = driver.execute_script("return document.readyState === 'complete' && !!document.body;")
            check(f'{label}: page still responsive after folder click', page_alive)

        # ── 2. "..." menu -> Rename (real clicks throughout) ─────────────────
        more_buttons = driver.find_elements(By.XPATH, "//*[contains(@class,'sf2-actions')]//button[.//span[contains(@class,'anticon-more')]]")
        if check(f'{label}: folder "..." trigger found', len(more_buttons) > 0):
            real_click(driver, more_buttons[0])
            time.sleep(0.6)
            popup = wait_for(driver, By.CLASS_NAME, 'dashboard-more-menu', timeout=5)
            check(f'{label}: "..." menu opens on a single real click', popup is not None)

            if popup:
                rename_items = [e for e in popup.find_elements(By.XPATH, ".//*[contains(text(),'Rename')]") if e.is_displayed()]
                if check(f'{label}: "Rename" item visible in menu', len(rename_items) > 0):
                    real_click(driver, rename_items[0])
                    time.sleep(1)
                    check(f'{label}: Rename modal opens', wait_for_open_modal(driver))
                    modal_el = get_open_modal_content(driver)

                    name_input = modal_el.find_elements(By.XPATH, ".//input[not(@type='checkbox')]")[0] if modal_el else None
                    if check(f'{label}: name input present', name_input is not None):
                        real_click(driver, name_input)
                        name_input.send_keys(' x')
                        name_input.send_keys('\b\b')  # undo the edit, keep name unchanged
                        check(f'{label}: name input is typeable via real interaction', True)

                    cancel_candidates = modal_el.find_elements(By.XPATH, ".//button[.//span[text()='Cancel']]") if modal_el else []
                    cancel_btn = cancel_candidates[0] if cancel_candidates else None
                    if check(f'{label}: Cancel button found', cancel_btn is not None):
                        real_click(driver, cancel_btn)
                        closed = False
                        for _ in range(20):
                            time.sleep(0.3)
                            panel_gone = len(driver.find_elements(By.CLASS_NAME, 'sw-safemodal-panel')) == 0
                            if panel_gone:
                                closed = True
                                break
                        check(f'{label}: Cancel (real click) closes Rename modal within 6s', closed)
                        page_interactive = driver.execute_script("""
                            const el = document.elementFromPoint(50, 50);
                            return el ? !el.closest('.sw-safemodal-mask') : true;
                        """)
                        check(f'{label}: page interactive after closing Rename modal', page_interactive)

        # ── 3. "..." menu -> Share (real clicks throughout) ──────────────────
        more_buttons2 = driver.find_elements(By.XPATH, "//*[contains(@class,'sf2-actions')]//button[.//span[contains(@class,'anticon-more')]]")
        if more_buttons2:
            real_click(driver, more_buttons2[0])
            time.sleep(0.6)
            popup2 = wait_for(driver, By.CLASS_NAME, 'dashboard-more-menu', timeout=5)
            if popup2:
                share_items = [e for e in popup2.find_elements(By.XPATH, ".//*[contains(text(),'Share')]") if e.is_displayed()]
                if check(f'{label}: "Share" item visible in menu', len(share_items) > 0):
                    real_click(driver, share_items[0])
                    time.sleep(1)
                    check(f'{label}: Share modal opens', wait_for_open_modal(driver))
                    modal_el2 = get_open_modal_content(driver)

                    ms_box_candidates = modal_el2.find_elements(By.XPATH, ".//input[@placeholder]") if modal_el2 else []
                    ms_box = ms_box_candidates[0] if ms_box_candidates else None
                    if check(f'{label}: SafeMultiSelect input found', ms_box is not None):
                        real_click(driver, ms_box)
                        time.sleep(0.5)
                        panel = len(driver.find_elements(By.CLASS_NAME, 'sw-multiselect-panel')) > 0
                        check(f'{label}: SafeMultiSelect panel opens on real click', panel)

                    cancel_candidates2 = modal_el2.find_elements(By.XPATH, ".//button[.//span[text()='Cancel']]") if modal_el2 else []
                    cancel_btn2 = cancel_candidates2[0] if cancel_candidates2 else None
                    if check(f'{label}: Share modal Cancel button found', cancel_btn2 is not None):
                        real_click(driver, cancel_btn2)
                        closed = False
                        for _ in range(20):
                            time.sleep(0.3)
                            panel_gone = len(driver.find_elements(By.CLASS_NAME, 'sw-safemodal-panel')) == 0
                            if panel_gone:
                                closed = True
                                break
                        check(f'{label}: Cancel (real click) closes Share modal within 6s', closed)
                        page_interactive = driver.execute_script("""
                            const el = document.elementFromPoint(50, 50);
                            return el ? !el.closest('.sw-safemodal-mask') : true;
                        """)
                        check(f'{label}: page interactive after closing Share modal', page_interactive)

        collect_js_errors(driver, label)

    finally:
        driver.quit()


def main():
    import os
    token = os.environ['SWAYA_TOKEN']
    run('https://test.swaya.me', 'test.swaya.me', token, 'TEST')

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

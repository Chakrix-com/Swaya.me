"""
Investigates the reported bug: the folder pane's "..." menu (Share /
New subfolder / Rename-Move / Delete) looks odd -- wrong font, no proper
look and feel.

Hypothesis: SidebarFolderTree.jsx is imported eagerly in App.jsx (part of the
persistent layout, present on every authenticated route), and its folder
"..." menu is rendered by MoreActionsMenu.jsx with className
"dashboard-more-menu" / "dashboard-more-menu-item" etc. But those classes are
only DEFINED in features/dashboard/Dashboard.css, which is bundled into the
Dashboard route's own lazy-loaded JS chunk (Dashboard.jsx does `import
'./Dashboard.css'`). So the menu is only styled correctly if that CSS chunk
has already been loaded -- i.e. only if the user has visited /dashboard at
some point in this session. On any other route reached without first
loading /dashboard, the menu would render with browser default styles
(no border-radius, no padding, no hover states, generic font) -- exactly
matching "font and look and feel looks odd".

This script opens a FRESH browser session (no prior page loads), navigates
STRAIGHT to a non-dashboard route (/activities), opens a folder's "..."
menu, and captures computed styles for a menu item to check whether
Dashboard.css's rules actually applied. Takes screenshots on both
/dashboard and /activities for visual comparison.

Run:
    backend/.venv/bin/python3 scripts/selenium_folder_menu_style_check.py

Watch live at: http://www.swaya.me:7900 (noVNC -- no password)
"""
import socket
import subprocess
import sys
import time

socket.setdefaulttimeout(20)

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

sys.path.insert(0, '/home/vinay/Swaya.me/scripts')
from selenium_utils import inject_error_collectors, collect_js_errors  # noqa: E402

WEBDRIVER_URL = 'http://localhost:4444'
TARGET_BASE = 'https://www.swaya.me'
COOKIE_DOMAIN = 'www.swaya.me'
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
    return subprocess.check_output(args).decode().strip()


def open_folder_menu(driver):
    """Find the first real folder row in the sidebar and open its "..." menu.
    Returns the MoreActionsMenu popup element, or None."""
    rows = driver.find_elements(By.XPATH, "//*[contains(@class,'sf2-row')]")
    # skip "All Activities" virtual root (has no menu trigger)
    target_row = None
    for r in rows:
        if r.find_elements(By.TAG_NAME, 'button'):
            target_row = r
            break
    if not target_row:
        return None, None
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_row)
    time.sleep(0.3)
    btn = target_row.find_elements(By.TAG_NAME, 'button')[-1]
    driver.execute_script('arguments[0].click();', btn)
    time.sleep(0.6)
    popups = driver.find_elements(By.CLASS_NAME, 'dashboard-more-menu')
    return (popups[0] if popups else None), target_row


def inspect_menu_style(driver, popup):
    """Grab computed styles that should come from Dashboard.css if it loaded."""
    return driver.execute_script("""
        const popup = arguments[0];
        const item = popup.querySelector('.dashboard-more-menu-item');
        const popupStyle = getComputedStyle(popup);
        const itemStyle = item ? getComputedStyle(item) : null;
        return {
            popup: {
                borderRadius: popupStyle.borderRadius,
                boxShadow: popupStyle.boxShadow,
                padding: popupStyle.padding,
                background: popupStyle.backgroundColor,
            },
            item: itemStyle ? {
                fontSize: itemStyle.fontSize,
                borderRadius: itemStyle.borderRadius,
                padding: itemStyle.padding,
                display: itemStyle.display,
            } : null,
        };
    """, popup)


def main():
    token = get_token('meetnishant@gmail.com')

    driver = None
    try:
        driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=webdriver.ChromeOptions())
        driver.set_window_size(1440, 900)

        # Home page (marketing site, not the Dashboard route) just to set the
        # cookie on the right origin before navigating to the actual target.
        driver.get(TARGET_BASE)
        driver.delete_all_cookies()
        driver.add_cookie({
            'name': 'access_token', 'value': token, 'domain': COOKIE_DOMAIN,
            'path': '/', 'secure': True, 'httpOnly': True,
        })

        # Go STRAIGHT to a route whose lazy chunk does NOT import Dashboard.css
        # (confirmed via grep: ResultsHub.jsx has no CSS import at all) --
        # Dashboard.css's chunk should not have been requested by the browser yet.
        TEST_ROUTE = '/results'
        driver.get(f'{TARGET_BASE}{TEST_ROUTE}')
        time.sleep(3)
        inject_error_collectors(driver)

        popup, row = open_folder_menu(driver)
        check(f'Folder "..." menu opens on {TEST_ROUTE}', popup is not None)
        if popup:
            style = inspect_menu_style(driver, popup)
            print(f'{INFO} {TEST_ROUTE} menu computed style: {style}')
            driver.save_screenshot('/home/vinay/Swaya.me/scripts/folder_menu_on_results.png')

            styled = style['popup']['borderRadius'] not in ('0px', '', None) and style['item'] is not None \
                and style['item']['borderRadius'] not in ('0px', '', None)
            if not styled:
                print(f'{FAIL} Menu on {TEST_ROUTE} appears UNSTYLED (Dashboard.css rules not applied)')
                issues.append(f'folder menu unstyled on {TEST_ROUTE} (Dashboard.css chunk not loaded)')
            else:
                print(f'{PASS} Menu on {TEST_ROUTE} picked up Dashboard.css styling')

            # close the popup before navigating away
            driver.execute_script('document.body.click();')
            time.sleep(0.3)

        collect_js_errors(driver, f'Folder menu style ({TEST_ROUTE})')

        # Now compare against /dashboard, where Dashboard.css IS loaded (by definition)
        driver.get(f'{TARGET_BASE}/dashboard')
        time.sleep(3)
        popup2, row2 = open_folder_menu(driver)
        check('Folder "..." menu opens on /dashboard', popup2 is not None)
        if popup2:
            style2 = inspect_menu_style(driver, popup2)
            print(f'{INFO} /dashboard menu computed style: {style2}')
            driver.save_screenshot('/home/vinay/Swaya.me/scripts/folder_menu_on_dashboard.png')

        collect_js_errors(driver, 'Folder menu style (/dashboard)')

    finally:
        if driver:
            driver.quit()

    print(f'\n{"="*60}')
    if issues:
        print(f'{FAIL} {len(issues)} issue(s): {issues}')
        sys.exit(1)
    else:
        print(f'{PASS} All checks passed')


if __name__ == '__main__':
    main()

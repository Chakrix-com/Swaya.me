"""
Reproduces the reported bug: Move-to-Folder's SafeTreeSelect dropdown list
gets clipped/hidden once there are more than ~2-3 folders.

Root cause hypothesis: SafeModal's body (`sw-safemodal-body`) has
`overflow-y: auto` (added in the "constrain panel height" fix), while
SafeTreeSelect's dropdown panel is deliberately NOT portaled -- it's a
nested `position: absolute` child so it stays in the modal's stacking
context. A CSS `overflow` other than `visible` on an ancestor clips any
descendant -- including absolutely-positioned ones -- that paints outside
the ancestor's border box. With few folders the dropdown fits inside the
body's existing box; with more, it needs more height than the body's
box provides and gets clipped by that overflow.

Creates N throwaway folders + 1 quiz via API, opens the Move-to-Folder
modal, opens the picker, and checks whether the LAST folder's option row
is actually visible (not clipped) via getBoundingClientRect vs the modal
body's clipping rect. Takes a screenshot either way. Cleans up after.

Run:
    backend/.venv/bin/python3 scripts/selenium_move_to_folder_overflow_check.py

Watch live at: http://www.swaya.me:7900 (noVNC -- no password)
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
SCREENSHOT = '/home/vinay/Swaya.me/scripts/move_to_folder_overflow.png'

PASS = '\033[92m PASS\033[0m'
FAIL = '\033[91m FAIL\033[0m'
INFO = '\033[94m INFO\033[0m'

issues = []
N_FOLDERS = 8


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
    folder_ids = []
    last_folder_name = None
    for i in range(N_FOLDERS):
        name = f'Overflow Test Folder {stamp}-{i}'
        res = requests.post(f'{API}/quizzes/folders', json={'name': name}, headers=headers)
        if not check(f'Created folder {i+1}/{N_FOLDERS}', res.status_code in (200, 201)):
            print(res.text)
            sys.exit(1)
        folder_ids.append(res.json()['id'])
        last_folder_name = name  # the one at the bottom of the list

    quiz_title = f'Overflow Test Quiz {stamp}'
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

        rows = [r for r in driver.find_elements(By.XPATH, "//table//tr") if quiz_title in r.text]
        if not check('Throwaway quiz row visible on dashboard', len(rows) > 0):
            sys.exit(1)
        row = rows[0]

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
        if not panel:
            sys.exit(1)

        tree_trigger = panel.find_element(By.XPATH, ".//div[@style[contains(., 'cursor: pointer')]][1]")
        driver.execute_script('arguments[0].click();', tree_trigger)
        time.sleep(0.5)

        # Dropdown is now portaled to document.body (outside `panel`), not nested inside
        # it. Folder names also appear in the sidebar folder tree (behind the modal
        # mask) -- scope to SafeTreeSelect's option span specifically via its inline
        # ellipsis style, which the sidebar's sf2-label span doesn't have.
        options = driver.find_elements(
            By.XPATH,
            f"//span[contains(@style, 'text-overflow: ellipsis') and contains(text(), '{last_folder_name}')]",
        )
        check(f'Last folder ({last_folder_name}) option is present in DOM', len(options) > 0)

        driver.save_screenshot(SCREENSHOT)
        print(f'{INFO} Screenshot saved to {SCREENSHOT}')

        if options:
            last_opt = options[0]
            # The dropdown's own list container is *meant* to be a scrollable
            # maxHeight box (that's normal, expected UX for a long option list).
            # The real question: after scrolling that container's own scrollbar
            # to the bottom, does the last option become reachable/visible, or
            # is it clipped by something ABOVE that container (e.g. a modal
            # body) that scrolling the dropdown itself can never reveal?
            result = driver.execute_script("""
                const el = arguments[0];
                // nearest scrollable ancestor = the dropdown's own list box
                let scrollBox = el.parentElement;
                while (scrollBox) {
                    const style = getComputedStyle(scrollBox);
                    if ((style.overflowY === 'auto' || style.overflowY === 'scroll')
                        && scrollBox.scrollHeight > scrollBox.clientHeight) break;
                    scrollBox = scrollBox.parentElement;
                }
                if (scrollBox) scrollBox.scrollTop = scrollBox.scrollHeight;

                const rect = el.getBoundingClientRect();
                // now look for clipping *above* the dropdown's own scroll box
                let clippedBy = null;
                let node = scrollBox ? scrollBox.parentElement : el.parentElement;
                while (node) {
                    const style = getComputedStyle(node);
                    if (style.overflow !== 'visible' || style.overflowY !== 'visible') {
                        const anc = node.getBoundingClientRect();
                        if (rect.bottom > anc.bottom + 0.5 || rect.top < anc.top - 0.5) {
                            clippedBy = node.className || node.tagName;
                            break;
                        }
                    }
                    node = node.parentElement;
                }
                return {
                    rect: {top: rect.top, bottom: rect.bottom, height: rect.height},
                    inViewport: rect.top >= 0 && rect.bottom <= window.innerHeight,
                    clippedBy: clippedBy,
                    displayed: el.offsetParent !== null,
                    hadOwnScrollBox: !!scrollBox,
                };
            """, last_opt)
            print(f'{INFO} Last option geometry (after scrolling dropdown to bottom): {result}')

            is_clipped = result['clippedBy'] is not None
            if is_clipped:
                print(f'{FAIL} Last folder option IS clipped by an ancestor above the dropdown\'s own scroll box: {result["clippedBy"]}')
                issues.append('dropdown option clipped by an ancestor outside its own scrollable list')
            else:
                print(f'{PASS} Last folder option reachable by scrolling the dropdown\'s own list (not clipped by anything above it)')

            check('Last folder option is selectable (Selenium is_displayed)', last_opt.is_displayed())

        collect_js_errors(driver, 'Move to Folder overflow check')

    finally:
        if driver:
            driver.quit()
        requests.delete(f'{API}/quizzes/{quiz_id}', headers=headers)
        for fid in folder_ids:
            requests.delete(f'{API}/quizzes/folders/{fid}', headers=headers)
        print(f'{INFO} Cleaned up throwaway quiz {quiz_id} and {len(folder_ids)} folders')

    print(f'\n{"="*60}')
    if issues:
        print(f'{FAIL} {len(issues)} issue(s): {issues}')
        sys.exit(1)
    else:
        print(f'{PASS} All checks passed')


if __name__ == '__main__':
    main()

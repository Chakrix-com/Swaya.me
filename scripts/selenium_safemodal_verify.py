"""
Selenium verification for SafeModal replacing antd Modal across the two
flows reported as hanging on the user's office VDI: folder create/rename/
delete/share (SidebarFolderTree.jsx) and the post-publish result modals in
QuizBuilder.jsx (poll link, exam link).

This does NOT verify the VDI race itself — a JS-level .click() never fires a
real mousedown, so it can't exercise the RDP input-redirection race that
caused the original bug (see safemodal-vdi-freeze-plan.md §6). It only
confirms nothing regressed: modals open/close, forms submit, footers work,
no new console errors, no visual/z-index issues. The batch-continuity
confirm modal (QuizBuilder's batchConfirmModal) is not exercised here — it
only appears when republishing an exam that already has a prior completed
session, which needs a full participant run to set up and is out of scope
for this pass.

Run:
    sudo docker exec selenium-arm python3 /scripts/selenium_safemodal_verify.py

Watch live at: http://www.swaya.me:7900 (noVNC — no password)
"""
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

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
# Runs inside the seleniarm container (bridge network) — localhost:8001
# doesn't reach the host backend from there, but the public hostname does
# (nginx on the host proxies it), so the API is addressed the same way the
# browser addresses it rather than via the host-only backend port.
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


def wait_modal_closed(driver, timeout=6):
    end = time.time() + timeout
    while time.time() < end:
        if len(driver.find_elements(By.CLASS_NAME, 'sw-safemodal-panel')) == 0:
            return True
        time.sleep(0.2)
    return False


def get_token():
    import os
    env_token = os.environ.get('SWAYA_TOKEN', '').strip()
    if env_token:
        return env_token
    try:
        return subprocess.check_output([PYTHON, TOKEN_SCRIPT]).decode().strip()
    except Exception as e:
        print(f'{FAIL} Token generation failed: {e}')
        sys.exit(1)


def create_offline_poll(token):
    headers = {'Authorization': f'Bearer {token}'}
    start = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    res = requests.post(f'{API}/quizzes/', json={
        'title': 'SafeModal Selenium Poll Test',
        'quiz_type': 'offline_poll',
        'offline_start_at': start,
        'offline_end_at': end,
    }, headers=headers)
    if res.status_code not in (200, 201):
        print(f'{FAIL} Create offline poll quiz failed: {res.status_code} {res.text}')
        return None
    quiz_id = res.json()['id']
    requests.post(f'{API}/quizzes/{quiz_id}/questions', json={
        'question_type': 'mcq', 'text': 'What is 2 + 2?',
        'options': ['3', '4', '5', '6'], 'correct_answer_index': 1, 'points': 1,
    }, headers=headers)
    return quiz_id


def create_exam(token):
    headers = {'Authorization': f'Bearer {token}'}
    start = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    res = requests.post(f'{API}/quizzes/', json={
        'title': 'SafeModal Selenium Exam Test',
        'quiz_type': 'exam',
        'exam_start_at': start,
        'exam_end_at': end,
        'exam_time_limit_seconds': 1800,
    }, headers=headers)
    if res.status_code not in (200, 201):
        print(f'{FAIL} Create exam quiz failed: {res.status_code} {res.text}')
        return None
    quiz_id = res.json()['id']
    requests.post(f'{API}/quizzes/{quiz_id}/questions', json={
        'question_type': 'mcq', 'text': 'What is 3 + 3?',
        'options': ['5', '6', '7', '8'], 'correct_answer_index': 1, 'points': 1,
    }, headers=headers)
    return quiz_id


def wait_for_folder_row(driver, name, timeout=6, expect_present=True):
    """Poll for a folder row by name. handleRename/handleCreate/handleDelete
    all close the SafeModal (setXOpen(false)) BEFORE awaiting
    reloadFolders() — so the modal-closed signal races ahead of the tree
    refetch landing. A one-shot check right after wait_modal_closed() can
    read stale tree state; poll instead."""
    end = time.time() + timeout
    while time.time() < end:
        row = get_folder_row(driver, name)
        if (row is not None) == expect_present:
            return row if expect_present else True
        time.sleep(0.3)
    return get_folder_row(driver, name) if expect_present else (get_folder_row(driver, name) is None)


def get_folder_row(driver, name):
    """Re-query by current display name every time — SidebarFolderTree calls
    reloadFolders() after create/rename/delete, which re-renders the tree
    with fresh DOM nodes, so any previously-captured element reference goes
    stale (detached from the document) even though the folder itself still
    exists."""
    labels = [e for e in driver.find_elements(By.CSS_SELECTOR, '.sf2-label') if e.text == name]
    if not labels:
        return None
    return labels[0].find_element(By.XPATH, '..')


def open_folder_menu(driver, name):
    row = get_folder_row(driver, name)
    if row is None:
        return None
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", row)
    time.sleep(0.3)
    triggers = row.find_elements(By.XPATH, ".//button[.//span[contains(@class,'anticon-more')]]")
    return triggers[0] if triggers else None


def test_folder_flows(driver):
    print(f'\n{INFO} --- Folder create/rename/share/delete (SidebarFolderTree) ---')
    driver.get(f'{TARGET_BASE}/dashboard')
    time.sleep(3)
    inject_error_collectors(driver)

    folder_name = f'SafeModal Test {int(time.time())}'

    # ── Create ────────────────────────────────────────────────────────────
    # .sf2-header-add is opacity:0 until .sf2-container is hovered (CSS-only
    # reveal-on-hover), so it's present but not Selenium-"visible" — use
    # presence, not visibility, then click via JS same as everywhere else.
    add_btn = wait_for(driver, By.CSS_SELECTOR, '.sf2-header-add', timeout=10, visible=False)
    if not check('Sidebar: "+ New Folder" trigger found', add_btn is not None):
        return
    driver.execute_script('arguments[0].click();', add_btn)
    time.sleep(0.5)

    panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
    if not check('Create-folder SafeModal opened', panel is not None):
        return

    name_input = wait_for(driver, By.XPATH, "//div[contains(@class,'sw-safemodal-body')]//input", timeout=5)
    if not check('Create-folder name input found', name_input is not None):
        return
    name_input.send_keys(folder_name)

    footer_buttons = driver.find_elements(By.XPATH, "//div[contains(@class,'sw-safemodal-footer')]//button")
    if not check('Create-folder footer has Cancel + OK buttons', len(footer_buttons) >= 2):
        return
    driver.execute_script('arguments[0].click();', footer_buttons[-1])
    time.sleep(1)

    check('Create-folder modal closes after Create', wait_modal_closed(driver))

    current_name = folder_name
    if not check('Newly created folder appears in tree', wait_for_folder_row(driver, current_name) is not None):
        collect_js_errors(driver, 'Folder create')
        return

    # ── Rename ────────────────────────────────────────────────────────────
    more_btn = open_folder_menu(driver, current_name)
    if not check('Folder "..." trigger found (for Rename)', more_btn is not None):
        collect_js_errors(driver, 'Folder rename')
        return
    driver.execute_script('arguments[0].click();', more_btn)
    time.sleep(0.5)
    rename_items = [e for e in driver.find_elements(By.XPATH, "//*[contains(text(),'Rename')]") if e.is_displayed()]
    if not check('"Rename" menu item found', len(rename_items) > 0):
        collect_js_errors(driver, 'Folder rename')
        return
    driver.execute_script('arguments[0].click();', rename_items[0])
    time.sleep(0.8)

    rename_panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
    check('Rename SafeModal opened', rename_panel is not None)
    if rename_panel:
        renamed_name = folder_name + ' renamed'
        rn_input = rename_panel.find_element(By.XPATH, ".//input[not(@type='checkbox')]")
        # .clear() is unreliable on this antd-controlled input (silently
        # no-ops here), leaving old text in place so send_keys() appends
        # instead of replacing. Select-all + type-over instead, like a real
        # user would.
        rn_input.send_keys(Keys.CONTROL, 'a')
        rn_input.send_keys(renamed_name)
        rn_footer_buttons = driver.find_elements(By.XPATH, "//div[contains(@class,'sw-safemodal-footer')]//button")
        driver.execute_script('arguments[0].click();', rn_footer_buttons[-1])
        time.sleep(1)
        check('Rename modal closes after Save', wait_modal_closed(driver))
        if check('Folder name updated in tree after rename', wait_for_folder_row(driver, renamed_name) is not None):
            current_name = renamed_name

    # ── Share ─────────────────────────────────────────────────────────────
    more_btn2 = open_folder_menu(driver, current_name)
    if more_btn2:
        driver.execute_script('arguments[0].click();', more_btn2)
        time.sleep(0.5)
        share_items = [e for e in driver.find_elements(By.XPATH, "//*[contains(text(),'Share')]") if e.is_displayed()]
        if check('"Share" menu item found', len(share_items) > 0):
            driver.execute_script('arguments[0].click();', share_items[0])
            time.sleep(1)
            share_panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
            check('Share SafeModal opened', share_panel is not None)
            if share_panel:
                ms_input = wait_for(driver, By.XPATH, "//div[contains(@class,'sw-safemodal-body')]//input[@placeholder]", timeout=5)
                check('SafeMultiSelect input found inside Share SafeModal', ms_input is not None)
                if ms_input:
                    driver.execute_script('arguments[0].click();', ms_input)
                    time.sleep(0.5)
                    panel_open = len(driver.find_elements(By.CLASS_NAME, 'sw-multiselect-panel')) > 0
                    check('SafeMultiSelect dropdown not clipped by SafeModal body (opens fine)', panel_open)
                    # close the multiselect dropdown (its own overlay, z-index 1049),
                    # not the SafeModal mask (z-index 2000) behind it
                    ms_masks = driver.find_elements(By.CSS_SELECTOR, "div[style*='z-index: 1049']")
                    if ms_masks:
                        driver.execute_script('arguments[0].click();', ms_masks[0])
                        time.sleep(0.3)
                # Escape should close the whole SafeModal
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(0.6)
                check('Escape key closes Share SafeModal', wait_modal_closed(driver))

    collect_js_errors(driver, 'Folder create/rename/share')

    # ── Delete ────────────────────────────────────────────────────────────
    more_btn3 = open_folder_menu(driver, current_name)
    if not check('Folder "..." trigger found (for Delete)', more_btn3 is not None):
        return
    driver.execute_script('arguments[0].click();', more_btn3)
    time.sleep(0.5)
    delete_items = [e for e in driver.find_elements(By.XPATH, "//*[contains(text(),'Delete')]") if e.is_displayed()]
    if not check('"Delete" menu item found', len(delete_items) > 0):
        return
    driver.execute_script('arguments[0].click();', delete_items[0])
    time.sleep(0.8)

    delete_panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
    check('Delete SafeModal opened', delete_panel is not None)
    if delete_panel:
        del_footer_buttons = driver.find_elements(By.XPATH, "//div[contains(@class,'sw-safemodal-footer')]//button")
        check('Delete footer has Cancel + Delete buttons', len(del_footer_buttons) >= 2)
        driver.execute_script('arguments[0].click();', del_footer_buttons[-1])
        time.sleep(1)
        check('Delete modal closes after confirming', wait_modal_closed(driver))
        check('Folder removed from tree after delete', wait_for_folder_row(driver, current_name, expect_present=False))

    collect_js_errors(driver, 'Folder delete')


def test_publish_flow(driver, quiz_id, quiz_kind, publish_button_text, result_close_button_texts):
    print(f'\n{INFO} --- Publish flow: {quiz_kind} (quiz {quiz_id}) ---')
    driver.get(f'{TARGET_BASE}/quiz/{quiz_id}/edit')
    time.sleep(3)
    inject_error_collectors(driver)

    publish_btns = [e for e in driver.find_elements(By.XPATH, f"//button[.//span[contains(text(),'{publish_button_text}')]]") if e.is_displayed()]
    if not check(f'{quiz_kind}: Publish button found', len(publish_btns) > 0):
        driver.save_screenshot(f'/tmp/safemodal_{quiz_kind}_no_publish_btn.png')
        return
    driver.execute_script('arguments[0].scrollIntoView({block:"center"});', publish_btns[0])
    time.sleep(0.3)
    driver.execute_script('arguments[0].click();', publish_btns[0])
    time.sleep(2)

    panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=10)
    if not check(f'{quiz_kind}: result SafeModal opened after publish', panel is not None):
        driver.save_screenshot(f'/tmp/safemodal_{quiz_kind}_no_result_modal.png')
        collect_js_errors(driver, f'{quiz_kind} publish')
        return

    footer_buttons = driver.find_elements(By.XPATH, "//div[contains(@class,'sw-safemodal-footer')]//button")
    check(f'{quiz_kind}: result modal footer has expected button count', len(footer_buttons) == len(result_close_button_texts))

    body_text = panel.find_element(By.CLASS_NAME, 'sw-safemodal-body').text
    check(f'{quiz_kind}: result modal body shows a link', ('http' in body_text) or ('/' in body_text))

    close_btn = None
    for btn in footer_buttons:
        if any(t.lower() in btn.text.lower() for t in result_close_button_texts):
            close_btn = btn
            break
    if not check(f'{quiz_kind}: a close/cancel button found in footer', close_btn is not None):
        return
    driver.execute_script('arguments[0].click();', close_btn)
    time.sleep(1)
    check(f'{quiz_kind}: result modal closes on footer button click', wait_modal_closed(driver))

    collect_js_errors(driver, f'{quiz_kind} publish result')


def main():
    print(f'{INFO} Generating JWT token...')
    token = get_token()
    print(f'{PASS} Token ready ({token[:30]}...)')

    print(f'{INFO} Creating test offline-poll quiz via API...')
    poll_quiz_id = create_offline_poll(token)
    check('Offline poll quiz created via API', poll_quiz_id is not None)

    print(f'{INFO} Creating test exam quiz via API...')
    exam_quiz_id = create_exam(token)
    check('Exam quiz created via API', exam_quiz_id is not None)

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

        test_folder_flows(driver)

        if poll_quiz_id:
            test_publish_flow(driver, poll_quiz_id, 'Offline Poll', 'Publish & Activate', ['cancel'])
        if exam_quiz_id:
            test_publish_flow(driver, exam_quiz_id, 'Exam', 'Publish & Activate', ['results', 'cancel'])

        print(f'\n{"="*70}')
        print(f'{INFO} NOTE: this pass confirms no regression only. It does NOT verify')
        print(f'{INFO} the actual VDI mousedown-race — that requires hands-on testing on')
        print(f'{INFO} the real office VDI machine (plan §6 / task T10).')
        print(f'{"="*70}')

        if issues:
            print(f'{FAIL} {len(issues)} issue(s) found:')
            for i in issues:
                print(f'  - {i}')
        else:
            print(f'{PASS} All checks passed.')
    finally:
        driver.quit()

    sys.exit(1 if issues else 0)


if __name__ == '__main__':
    main()

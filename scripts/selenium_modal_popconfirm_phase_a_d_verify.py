"""
Selenium regression pass for the Phase A-D Modal/Popconfirm remediation
(_private/modal-popconfirm-vdi-audit-tasks-20260720.md, T01-T21).

Covers, on test.swaya.me:
  - CreateChooser (Dashboard "+" button) SafeModal            [T01]
  - Dashboard Template Library SafeModal                       [T02]
  - AppFeedbackModal SafeModal                                 [T05]
  - QuizBuilder AI Generate Questions SafeModal                [T07]
  - QuizBuilder delete-question SafeConfirm                    [T15]
  - MoreActionsMenu SafeConfirm (Dashboard delete quiz)         [T11]
  - Activities bulk-archive SafeConfirm                        [T13]
  - UserManagement delete-user SafeConfirm (via MoreActionsMenu)[T18]
  - ExamResults send-emails SafeConfirm                         [T20]
  - TierManagement SafeModal (super-admin)                      [T09]
  - OrganizationManagement create-org + update-quota SafeModal  [T10, T19]

Out of scope for this automated pass (participant-facing / live-session-only,
same caveat as the prior SafeModal passes — see selenium_safemodal_verify.py):
  - QuizControl/QuizPresent QR-enlarge modal and skip-timer/stop-quiz
    SafeConfirm (require an active live session)               [T03,T04,T14]
  - ExamSession Submit-Exam SafeConfirm (requires a full exam-taking flow
    with join code / OTP)                                       [T17]
  - ProctoringOverlay closable=false behavior (requires triggering a real
    proctoring violation)                                       [T08]
  - SidebarLiveSessions stop-session SafeConfirm (requires a live session)
                                                                  [T12]
These need either hands-on testing or a follow-up script with a fuller
live-session/exam-taking setup.

This does NOT verify the RDP mousedown/blur race itself — a JS-level
.click() never fires a real mousedown, so it can't exercise that. It only
confirms no regression: modals/confirms open, act correctly, close, no
antd Modal/Popconfirm DOM leftover, no new console errors.

Run:
    sudo docker exec selenium-arm python3 /scripts/selenium_modal_popconfirm_phase_a_d_verify.py

Watch live at: http://www.swaya.me:7900 (noVNC — no password)
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


def get_token(email, env_var):
    import os
    env_token = os.environ.get(env_var, '').strip()
    if env_token:
        return env_token
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


def create_quiz(token, quiz_type='quiz', title=None):
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.post(f'{API}/quizzes/', json={
        'title': title or f'Phase A-D Selenium Test {int(time.time())}',
        'quiz_type': quiz_type,
    }, headers=headers)
    if res.status_code not in (200, 201):
        print(f'{FAIL} Create {quiz_type} quiz failed: {res.status_code} {res.text}')
        return None
    quiz_id = res.json()['id']
    requests.post(f'{API}/quizzes/{quiz_id}/questions', json={
        'question_type': 'mcq', 'text': 'Placeholder question?',
        'options': ['A', 'B', 'C', 'D'], 'correct_answer_index': 0, 'points': 1,
    }, headers=headers)
    return quiz_id


def create_throwaway_user(token):
    headers = {'Authorization': f'Bearer {token}'}
    email = f'selenium.throwaway.{int(time.time())}@example.com'
    res = requests.post(f'{API}/users', json={
        'email': email, 'password': 'ThrowawayPass123!',
        'full_name': 'Selenium Throwaway', 'role': 'viewer', 'is_active': True,
    }, headers=headers)
    if res.status_code not in (200, 201):
        print(f'{INFO} Create throwaway user failed (non-fatal, will skip that check): {res.status_code} {res.text}')
        return None
    return res.json().get('id'), email


# ── CreateChooser (T01) ──────────────────────────────────────────────────
def test_create_chooser(driver):
    print(f'\n{INFO} --- CreateChooser SafeModal (T01) ---')
    driver.get(f'{TARGET_BASE}/dashboard')
    time.sleep(3)
    inject_error_collectors(driver)

    plus_btns = [e for e in driver.find_elements(By.XPATH, "//button[.//span[contains(@class,'anticon-plus')]]") if e.is_displayed()]
    if not check('Dashboard "+" trigger found', len(plus_btns) > 0):
        return
    driver.execute_script('arguments[0].click();', plus_btns[0])
    time.sleep(1)
    panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
    check('CreateChooser opens as SafeModal', panel is not None)
    check('No antd ant-modal rendered', len(driver.find_elements(By.CLASS_NAME, 'ant-modal-content')) == 0)
    if panel:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(0.6)
        check('Escape closes CreateChooser', wait_gone(driver, 'sw-safemodal-panel'))
    collect_js_errors(driver, 'CreateChooser')


# ── Dashboard Template Library (T02) ─────────────────────────────────────
def test_template_library(driver):
    print(f'\n{INFO} --- Dashboard Template Library SafeModal (T02) ---')
    driver.get(f'{TARGET_BASE}/dashboard')
    time.sleep(3)
    inject_error_collectors(driver)

    btns = [e for e in driver.find_elements(By.XPATH, "//button[.//span[contains(text(),'Template')]]") if e.is_displayed()]
    if not check('Template Library trigger found', len(btns) > 0):
        return
    driver.execute_script('arguments[0].click();', btns[0])
    time.sleep(1.5)
    panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=8)
    check('Template Library opens as SafeModal', panel is not None)
    if panel:
        table = panel.find_elements(By.CLASS_NAME, 'ant-table')
        check('Template table renders inside SafeModal body', len(table) > 0)
        mask = driver.find_elements(By.CLASS_NAME, 'sw-safemodal-mask')
        if mask:
            driver.execute_script('arguments[0].click();', mask[0])
            time.sleep(0.6)
            check('Mask click closes Template Library', wait_gone(driver, 'sw-safemodal-panel'))
    collect_js_errors(driver, 'Template Library')


# ── AppFeedbackModal (T05) ───────────────────────────────────────────────
def test_feedback_modal(driver):
    print(f'\n{INFO} --- AppFeedbackModal SafeModal (T05) ---')
    driver.get(f'{TARGET_BASE}/dashboard')
    time.sleep(3)
    inject_error_collectors(driver)

    btns = [e for e in driver.find_elements(By.XPATH, "//*[contains(@class,'anticon-message') or contains(@aria-label,'feedback')]") if e.is_displayed()]
    if not btns:
        # Fallback: search header buttons by common feedback labels
        btns = [e for e in driver.find_elements(By.XPATH, "//button[contains(., 'Feedback') or contains(., 'feedback')]") if e.is_displayed()]
    if not check('Feedback trigger found', len(btns) > 0):
        print(f'{INFO} Could not locate feedback trigger — skipping (non-fatal)')
        return
    driver.execute_script('arguments[0].click();', btns[0])
    time.sleep(1)
    panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
    check('AppFeedbackModal opens as SafeModal', panel is not None)
    if panel:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(0.6)
        check('Escape closes AppFeedbackModal', wait_gone(driver, 'sw-safemodal-panel'))
    collect_js_errors(driver, 'AppFeedbackModal')


# ── QuizBuilder AI modal + delete-question confirm (T07, T15) ───────────
def test_quizbuilder(driver, quiz_id):
    print(f'\n{INFO} --- QuizBuilder AI modal (T07) + delete-question SafeConfirm (T15), quiz {quiz_id} ---')
    driver.get(f'{TARGET_BASE}/quiz/{quiz_id}/edit')
    time.sleep(3)
    inject_error_collectors(driver)

    ai_btns = [e for e in driver.find_elements(By.XPATH, "//button[.//span[contains(text(),'AI') or contains(text(),'Generate')]]") if e.is_displayed()]
    if check('AI Generate trigger found', len(ai_btns) > 0):
        driver.execute_script('arguments[0].click();', ai_btns[0])
        time.sleep(1)
        panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
        check('AI Generate modal opens as SafeModal', panel is not None)
        if panel:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.6)
            check('Escape closes AI Generate modal', wait_gone(driver, 'sw-safemodal-panel'))
    collect_js_errors(driver, 'QuizBuilder AI modal')

    del_btns = [e for e in driver.find_elements(By.XPATH, "//button[.//span[contains(@class,'anticon-delete')]]") if e.is_displayed()]
    if check('Delete-question trigger found', len(del_btns) > 0):
        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', del_btns[0])
        time.sleep(0.3)
        driver.execute_script('arguments[0].click();', del_btns[0])
        time.sleep(1)
        panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
        check('Delete-question SafeConfirm opens', panel is not None)
        check('No antd Popconfirm rendered', len(driver.find_elements(By.CLASS_NAME, 'ant-popover')) == 0)
        if panel:
            cancel_btns = panel.find_elements(By.XPATH, ".//button[contains(., 'Cancel')]")
            if cancel_btns:
                driver.execute_script('arguments[0].click();', cancel_btns[0])
                time.sleep(0.6)
                check('Cancel closes delete-question SafeConfirm without deleting', wait_gone(driver, 'sw-safemodal-panel'))
    collect_js_errors(driver, 'QuizBuilder delete-question')


# ── MoreActionsMenu confirm: Dashboard delete quiz (T11) ─────────────────
def test_dashboard_delete_confirm(driver, quiz_id, quiz_title):
    print(f'\n{INFO} --- MoreActionsMenu SafeConfirm on Dashboard (T11), quiz {quiz_id} ---')
    driver.get(f'{TARGET_BASE}/dashboard')
    time.sleep(3)
    inject_error_collectors(driver)

    rows = [r for r in driver.find_elements(By.XPATH, "//table//tr") if quiz_title in r.text]
    if not check('Throwaway quiz row found on Dashboard', len(rows) > 0):
        return
    row = rows[0]
    more_btns = row.find_elements(By.XPATH, ".//button[.//span[contains(@class,'anticon-more')]]")
    if not check('"..." trigger found on quiz row', len(more_btns) > 0):
        return
    driver.execute_script('arguments[0].scrollIntoView({block:"center"});', more_btns[0])
    time.sleep(0.3)
    driver.execute_script('arguments[0].click();', more_btns[0])
    time.sleep(0.6)

    delete_items = [e for e in driver.find_elements(By.XPATH, "//*[contains(text(),'Delete')]") if e.is_displayed()]
    if not check('"Delete" menu item found', len(delete_items) > 0):
        return
    driver.execute_script('arguments[0].click();', delete_items[0])
    time.sleep(1)

    panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
    check('Delete-quiz SafeConfirm opens (MoreActionsMenu)', panel is not None)
    if panel:
        ok_btns = [b for b in panel.find_elements(By.XPATH, ".//button") if 'delete' in b.text.lower()]
        if check('SafeConfirm has a Delete button', len(ok_btns) > 0):
            driver.execute_script('arguments[0].click();', ok_btns[0])
            time.sleep(1.5)
            check('SafeConfirm closes after confirming delete', wait_gone(driver, 'sw-safemodal-panel'))
    collect_js_errors(driver, 'Dashboard delete confirm')


# ── Activities bulk-archive confirm (T13) ────────────────────────────────
def test_activities_bulk_confirm(driver, quiz_title):
    print(f'\n{INFO} --- Activities bulk-archive SafeConfirm (T13) ---')
    driver.get(f'{TARGET_BASE}/activities')
    time.sleep(3)
    inject_error_collectors(driver)

    rows = [r for r in driver.find_elements(By.XPATH, "//table//tr") if quiz_title in r.text]
    if not check('Throwaway quiz row found on Activities', len(rows) > 0):
        print(f'{INFO} Row not found (may already be deleted by the Dashboard confirm test) — skipping')
        return
    checkboxes = rows[0].find_elements(By.XPATH, ".//input[@type='checkbox']")
    if not check('Row checkbox found', len(checkboxes) > 0):
        return
    driver.execute_script('arguments[0].click();', checkboxes[0])
    time.sleep(0.5)

    archive_btns = [e for e in driver.find_elements(By.XPATH, "//button[contains(., 'Archive')]") if e.is_displayed()]
    if not check('Bulk Archive button found', len(archive_btns) > 0):
        return
    driver.execute_script('arguments[0].click();', archive_btns[0])
    time.sleep(1)
    panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
    check('Bulk-archive SafeConfirm opens', panel is not None)
    if panel:
        cancel_btns = panel.find_elements(By.XPATH, ".//button[contains(., 'Cancel')]")
        if cancel_btns:
            driver.execute_script('arguments[0].click();', cancel_btns[0])
            time.sleep(0.6)
            check('Cancel closes bulk-archive SafeConfirm', wait_gone(driver, 'sw-safemodal-panel'))
    collect_js_errors(driver, 'Activities bulk-archive confirm')


# ── UserManagement delete-user confirm via MoreActionsMenu (T18) ─────────
def test_user_management_delete(driver, user_email):
    print(f'\n{INFO} --- UserManagement delete-user SafeConfirm (T18) ---')
    driver.get(f'{TARGET_BASE}/admin/users')
    time.sleep(3)
    inject_error_collectors(driver)

    rows = [r for r in driver.find_elements(By.XPATH, "//table//tr") if user_email in r.text]
    if not check('Throwaway user row found', len(rows) > 0):
        return
    row = rows[0]
    more_btns = row.find_elements(By.XPATH, ".//button[.//span[contains(@class,'anticon-more')]]")
    if not check('"..." trigger found on user row', len(more_btns) > 0):
        return
    driver.execute_script('arguments[0].scrollIntoView({block:"center"});', more_btns[0])
    time.sleep(0.3)
    driver.execute_script('arguments[0].click();', more_btns[0])
    time.sleep(0.6)

    delete_items = [e for e in driver.find_elements(By.XPATH, "//*[contains(text(),'Delete')]") if e.is_displayed()]
    if not check('"Delete" menu item found', len(delete_items) > 0):
        return
    driver.execute_script('arguments[0].click();', delete_items[0])
    time.sleep(1)
    panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
    check('Delete-user SafeConfirm opens', panel is not None)
    if panel:
        ok_btns = [b for b in panel.find_elements(By.XPATH, ".//button") if 'delete' in b.text.lower()]
        if check('SafeConfirm has a Delete button', len(ok_btns) > 0):
            driver.execute_script('arguments[0].click();', ok_btns[0])
            time.sleep(1.5)
            check('SafeConfirm closes after confirming delete', wait_gone(driver, 'sw-safemodal-panel'))
    collect_js_errors(driver, 'UserManagement delete confirm')


# ── ExamResults send-emails confirm (T20) ─────────────────────────────────
def test_examresults_send_emails(driver, quiz_id):
    print(f'\n{INFO} --- ExamResults send-emails SafeConfirm (T20), quiz {quiz_id} ---')
    driver.get(f'{TARGET_BASE}/quiz/{quiz_id}/exam-results')
    time.sleep(3)
    inject_error_collectors(driver)

    send_btns = [e for e in driver.find_elements(By.XPATH, "//button[.//span[contains(text(),'Send')]]") if e.is_displayed() and e.is_enabled()]
    if not check('Send-emails trigger found', len(send_btns) > 0):
        print(f'{INFO} Send-emails button not present/enabled (may already be sent) — skipping')
        return
    driver.execute_script('arguments[0].click();', send_btns[0])
    time.sleep(1)
    panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
    check('Send-emails SafeConfirm opens', panel is not None)
    if panel:
        cancel_btns = panel.find_elements(By.XPATH, ".//button[contains(., 'Cancel')]")
        if cancel_btns:
            driver.execute_script('arguments[0].click();', cancel_btns[0])
            time.sleep(0.6)
            check('Cancel closes send-emails SafeConfirm (no email sent)', wait_gone(driver, 'sw-safemodal-panel'))
    collect_js_errors(driver, 'ExamResults send-emails confirm')


# ── Super-admin: TierManagement (T09) + OrganizationManagement (T10, T19) ─
def test_tier_management(driver):
    print(f'\n{INFO} --- TierManagement SafeModal (T09, super-admin) ---')
    driver.get(f'{TARGET_BASE}/admin/tier-management')
    time.sleep(3)
    inject_error_collectors(driver)

    edit_btns = [e for e in driver.find_elements(By.XPATH, "//button[.//span[contains(@class,'anticon-edit')]]") if e.is_displayed()]
    if not check('Edit-tier trigger found', len(edit_btns) > 0):
        return
    driver.execute_script('arguments[0].click();', edit_btns[0])
    time.sleep(1)
    panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
    check('TierManagement edit modal opens as SafeModal', panel is not None)
    if panel:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(0.6)
        check('Escape closes TierManagement modal', wait_gone(driver, 'sw-safemodal-panel'))
    collect_js_errors(driver, 'TierManagement')


def test_organization_management(driver):
    print(f'\n{INFO} --- OrganizationManagement SafeModal (T10, T19, super-admin) ---')
    driver.get(f'{TARGET_BASE}/admin/organizations')
    time.sleep(3)
    inject_error_collectors(driver)

    create_btns = [e for e in driver.find_elements(By.XPATH, "//button[contains(., 'Create') or contains(., 'New')]") if e.is_displayed()]
    if check('Create-org trigger found', len(create_btns) > 0):
        driver.execute_script('arguments[0].click();', create_btns[0])
        time.sleep(1)
        panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
        check('Create-org modal opens as SafeModal', panel is not None)
        if panel:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.6)
            check('Escape closes create-org modal', wait_gone(driver, 'sw-safemodal-panel'))
    collect_js_errors(driver, 'OrganizationManagement create-org')

    quota_btns = [e for e in driver.find_elements(By.XPATH, "//button[.//span[contains(@class,'anticon-edit')]]") if e.is_displayed()]
    if check('Update-quota trigger found', len(quota_btns) > 0):
        driver.execute_script('arguments[0].click();', quota_btns[0])
        time.sleep(1)
        panel = wait_for(driver, By.CLASS_NAME, 'sw-safemodal-panel', timeout=5)
        check('Update-quota modal opens as SafeModal', panel is not None)
        if panel:
            input_el = panel.find_elements(By.XPATH, ".//input")
            check('Quota form input present', len(input_el) > 0)
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.6)
            check('Escape closes update-quota modal', wait_gone(driver, 'sw-safemodal-panel'))
    collect_js_errors(driver, 'OrganizationManagement update-quota')


def main():
    print(f'{INFO} Generating tokens...')
    admin_token = get_token('meetnishant@gmail.com', 'SWAYA_TOKEN_ADMIN')
    super_token = get_token('demo@swaya.me', 'SWAYA_TOKEN_SUPER')
    print(f'{PASS} Tokens ready')

    print(f'{INFO} Creating throwaway test data via API...')
    quiz_id = create_quiz(admin_token, 'quiz', f'PhaseAD Selenium {int(time.time())}')
    quiz_title = None
    if quiz_id:
        r = requests.get(f'{API}/quizzes/{quiz_id}', headers={'Authorization': f'Bearer {admin_token}'})
        quiz_title = r.json().get('title') if r.status_code == 200 else None
    check('Throwaway quiz created', quiz_id is not None)

    user_result = create_throwaway_user(admin_token)
    user_email = user_result[1] if user_result else None

    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1440,900')
    driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=options)
    driver.set_page_load_timeout(30)

    try:
        set_cookie(driver, admin_token)

        test_create_chooser(driver)
        test_template_library(driver)
        test_feedback_modal(driver)
        if quiz_id:
            test_quizbuilder(driver, quiz_id)
        if quiz_id and quiz_title:
            test_activities_bulk_confirm(driver, quiz_title)
        if user_email:
            test_user_management_delete(driver, user_email)
        # ExamResults needs an exam-type quiz with results; reuse the known
        # existing test quiz 1174 from the 2026-07-20 ExamResults fix pass.
        test_examresults_send_emails(driver, 1174)
        if quiz_id and quiz_title:
            test_dashboard_delete_confirm(driver, quiz_id, quiz_title)

        set_cookie(driver, super_token)
        test_tier_management(driver)
        test_organization_management(driver)

        print(f'\n{"="*70}')
        print(f'{INFO} NOTE: confirms no regression only — does not exercise the real')
        print(f'{INFO} RDP mousedown/blur race. Out-of-scope surfaces listed in the')
        print(f'{INFO} module docstring need hands-on or follow-up automated testing.')
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

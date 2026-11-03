"""
Selenium verification for three host-reported issues:

1. Save toasts must disappear on their own — even when the pointer sits on
   them (antd paused its timer on hover, which on a VDI meant forever) — and
   clicking Save 3 times must not leave 3 toasts on screen.
2. Test schedule start/end use a native date-time input: typed values are saved
   exactly, and an end before the start is refused.
3. Live quiz "Ask for real names": join screen shows no random name / dice,
   Join is disabled until a name is typed, and the API refuses a blank name.
   With the option off, the random name + dice are still offered.

Run:
    backend/.venv/bin/python3 scripts/selenium_vdi_toast_datetime_names_verify.py [shot_dir]
    VDI_FIX_ENV=live ...  # against www.swaya.me (throwaway quizzes, cleaned up)

Watch live at: http://www.swaya.me:7900 (noVNC — no password)
"""
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

LIVE = os.environ.get('VDI_FIX_ENV') == 'live'
DOMAIN = 'www.swaya.me' if LIVE else 'test.swaya.me'
BASE = f'https://{DOMAIN}'
API = f'{BASE}/api/v1'
WEBDRIVER_URL = 'http://localhost:4444'
TOKEN_SCRIPT = '/home/vinay/Swaya.me/scripts/generate_selenium_token.py'
PYTHON = '/home/vinay/Swaya.me/backend/.venv/bin/python3'
TOKEN_ENV_ARGS = ['--env', '/www/wwwroot/swaya-live/backend/.env'] if LIVE else []
SHOT_DIR = sys.argv[1] if len(sys.argv) > 1 else None

PASS = '\033[92m PASS\033[0m'
FAIL = '\033[91m FAIL\033[0m'
INFO = '\033[94m INFO\033[0m'
issues = []


def check(name, condition, detail=''):
    print(f'{PASS if condition else FAIL} {name}{(" — " + str(detail)) if detail != "" else ""}')
    if not condition:
        issues.append(name)
    return condition


def shot(driver, name):
    if SHOT_DIR:
        driver.save_screenshot(f'{SHOT_DIR}/{name}.png')


def button(driver, text):
    hits = [b for b in driver.find_elements(By.TAG_NAME, 'button') if b.is_displayed() and b.text.strip() == text]
    return hits[-1] if hits else None


def toasts(driver):
    return [t for t in driver.find_elements(By.CSS_SELECTOR, '.sw-message, .ant-message-notice') if t.is_displayed()]


def cleanup(headers, quiz_id):
    requests.post(f'{API}/quizzes/{quiz_id}/unpublish-exam', headers=headers)
    requests.post(f'{API}/quizzes/{quiz_id}/unpublish', headers=headers)
    d = requests.delete(f'{API}/quizzes/{quiz_id}', headers=headers)
    print(f'{INFO} Cleaned up throwaway quiz {quiz_id} (HTTP {d.status_code})')


def new_quiz(headers, title, quiz_type):
    r = requests.post(f'{API}/quizzes/', json={'title': title, 'quiz_type': quiz_type}, headers=headers)
    r.raise_for_status()
    quiz_id = r.json()['id']
    requests.post(f'{API}/quizzes/{quiz_id}/questions', headers=headers, json={
        'question_type': 'mcq', 'text': 'Question 1', 'options': ['A', 'B'], 'correct_answer_index': 0, 'points': 1,
    }).raise_for_status()
    return quiz_id


def open_setup(driver, quiz_id):
    driver.get(f'{BASE}/quiz/{quiz_id}/edit')
    time.sleep(5)
    rail = next((b for b in driver.find_elements(By.CSS_SELECTOR, '.qb-rail-entry') if 'Setup' in b.text), None)
    if rail:
        rail.click()
        time.sleep(1.5)


def set_native_datetime(driver, el, value):
    """Set a datetime-local input the way React sees a real edit."""
    driver.execute_script("""
        const el = arguments[0], v = arguments[1];
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
        setter.call(el, v);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    """, el, value)


def run_toast_and_dates(driver, headers, stamp):
    quiz_id = new_quiz(headers, f'Selenium VDI exam {stamp}', 'exam')
    try:
        # Host in India: a naive UTC timestamp read as local shifted the schedule 5h30 per save
        driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {'timezoneId': 'Asia/Kolkata'})
        open_setup(driver, quiz_id)
        inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="datetime-local"]')
        check('[dates] Schedule uses native date-time inputs (no antd picker)',
              len(inputs) >= 2 and not driver.find_elements(By.CSS_SELECTOR, '.ant-picker'), len(inputs))
        local_tz = driver.execute_script('return Intl.DateTimeFormat().resolvedOptions().timeZone')
        start_local = (datetime.now() + timedelta(days=2)).replace(hour=10, minute=15, second=0, microsecond=0)
        end_local = start_local + timedelta(hours=2, minutes=30)

        # End before start is refused
        set_native_datetime(driver, inputs[0], start_local.strftime('%Y-%m-%dT%H:%M'))
        set_native_datetime(driver, inputs[1], (start_local - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'))
        button(driver, 'Save Settings').click()
        time.sleep(1.5)
        body = driver.find_element(By.TAG_NAME, 'body').text
        shot(driver, 'dates_end_before_start')
        check('[dates] End before start shows a validation error', 'End must be after the start' in body)

        set_native_datetime(driver, inputs[1], end_local.strftime('%Y-%m-%dT%H:%M'))
        time.sleep(0.5)

        # Click Save three times quickly, with the pointer then parked on the toast
        save = button(driver, 'Save Settings')
        for _ in range(3):
            save.click()
            time.sleep(0.4)
        time.sleep(0.8)
        shown = toasts(driver)
        shot(driver, 'toasts_after_3_saves')
        check('[toast] Save toast appears', len(shown) >= 1, len(shown))
        check('[toast] 3 identical saves show ONE toast, not 3', len(shown) == 1, [t.text for t in shown])
        if shown:
            ActionChains(driver).move_to_element(shown[0]).perform()
        time.sleep(5)
        left = toasts(driver)
        shot(driver, 'toasts_after_wait')
        check('[toast] All toasts gone after ~5s, even with the pointer on one', len(left) == 0, len(left))

        q = requests.get(f'{API}/quizzes/{quiz_id}', headers=headers).json()
        print(f'{INFO} browser tz={local_tz}; saved start={q.get("exam_start_at")} end={q.get("exam_end_at")}')
        js = 'return new Date(arguments[0].endsWith("Z")||arguments[0].includes("+")?arguments[0]:arguments[0]+"Z").toLocaleString("sv-SE").slice(0,16).replace(" ","T")'
        saved_start = driver.execute_script(js, q.get('exam_start_at') or '')
        saved_end = driver.execute_script(js, q.get('exam_end_at') or '')
        check('[dates] Saved start equals what was entered', saved_start == start_local.strftime('%Y-%m-%dT%H:%M'),
              f'{saved_start} vs {start_local:%Y-%m-%dT%H:%M}')
        check('[dates] Saved end equals what was entered', saved_end == end_local.strftime('%Y-%m-%dT%H:%M'),
              f'{saved_end} vs {end_local:%Y-%m-%dT%H:%M}')

        # Reload: values come back into the inputs unchanged
        open_setup(driver, quiz_id)
        inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="datetime-local"]')
        vals = [i.get_attribute('value') for i in inputs[:2]]
        check('[dates] Reloaded inputs show the saved values',
              vals == [start_local.strftime('%Y-%m-%dT%H:%M'), end_local.strftime('%Y-%m-%dT%H:%M')], vals)
    finally:
        cleanup(headers, quiz_id)


def start_live(headers, quiz_id):
    requests.post(f'{API}/quizzes/{quiz_id}/publish', headers=headers)
    r = requests.post(f'{API}/quizzes/sessions/start', headers=headers, params={'quiz_id': quiz_id})
    if not r.ok:
        print(r.status_code, r.text[:300])
    r.raise_for_status()
    return r.json()['join_code'], r.json()['id']


def run_names(driver, headers, stamp, required):
    tag = f'[names:{"required" if required else "optional"}]'
    session_id = None
    quiz_id = new_quiz(headers, f'Selenium names {stamp} {required}', 'quiz')
    try:
        if required:
            # Toggle it on through the builder UI, like a host would
            open_setup(driver, quiz_id)
            row = next(d for d in driver.find_elements(By.XPATH, "//div[normalize-space(text())='Ask for real names']/../.."))
            row.find_element(By.CSS_SELECTOR, 'button.ant-switch').click()
            button(driver, 'Save').click()
            time.sleep(2)
        q = requests.get(f'{API}/quizzes/{quiz_id}', headers=headers).json()
        check(f'{tag} Setting saved as {required}', q.get('require_participant_name') is required, q.get('require_participant_name'))

        code, session_id = start_live(headers, quiz_id)
        look = requests.get(f'{API}/quizzes/sessions/lookup', params={'join_code': code}).json()
        check(f'{tag} Lookup reports require_participant_name={required}', look.get('require_participant_name') is required, look)

        driver.delete_all_cookies()
        driver.get(f'{BASE}/join/{code}')
        time.sleep(4)
        name_input = driver.find_element(By.CSS_SELECTOR, 'input.aj-input')
        dice = driver.find_elements(By.CSS_SELECTOR, '.aj-btn--reroll')
        join = driver.find_element(By.CSS_SELECTOR, '.aj-btn--join')
        shot(driver, f'join_{"required" if required else "optional"}')
        if required:
            check(f'{tag} Name field starts empty (no random name)', name_input.get_attribute('value') == '', name_input.get_attribute('value'))
            check(f'{tag} No dice / random-name button', not dice)
            check(f'{tag} Join disabled while name is blank', not join.is_enabled())
            blank = requests.post(f'{API}/quizzes/sessions/join', json={'join_code': code, 'display_name': '   '})
            check(f'{tag} API refuses a blank name', blank.status_code == 400, f'{blank.status_code} {blank.text[:80]}')
            name_input.send_keys('Saket Test')
            time.sleep(0.3)
            check(f'{tag} Join enabled once a name is typed', join.is_enabled())
            join.click()
            time.sleep(4)
            check(f'{tag} Joined the session with the typed name', '/session/' in driver.current_url, driver.current_url)
        else:
            check(f'{tag} Random name pre-filled', bool(name_input.get_attribute('value')), name_input.get_attribute('value'))
            check(f'{tag} Dice button offered', bool(dice))
            ok = requests.post(f'{API}/quizzes/sessions/join', json={'join_code': code})
            check(f'{tag} Anonymous join still allowed', ok.status_code == 200, ok.status_code)
    finally:
        if session_id:
            requests.post(f'{API}/quizzes/sessions/{session_id}/end', headers=headers)
        cleanup(headers, quiz_id)


def run_toast_mixed(driver):
    """Different messages still stack; a repeated one is not duplicated."""
    driver.get(f'{BASE}/dashboard')
    time.sleep(4)
    driver.find_element(By.CSS_SELECTOR, '.ant-float-btn').click()
    time.sleep(1.5)
    paste = """
        const done = arguments[arguments.length - 1];
        const c = document.createElement('canvas'); c.width = 60; c.height = 40;
        c.getContext('2d').fillRect(0, 0, 60, 40);
        c.toBlob((blob) => {
          const dt = new DataTransfer();
          dt.items.add(new File([blob], 'p.png', { type: 'image/png' }));
          document.querySelector('.ProseMirror').dispatchEvent(
            new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
          done();
        }, 'image/png');"""
    for _ in range(5):  # 4th and 5th are over the limit -> same warning twice
        driver.execute_async_script(paste)
        time.sleep(0.3)
    warn = [t.text for t in toasts(driver)]
    check('[toast] Repeated limit warning shows once', warn.count('You can attach up to 3 images') == 1, warn)
    # A different message while the warning is up: a >5 MB image -> size error
    driver.execute_script("""
        const big = new File([new Uint8Array(6 * 1024 * 1024)], 'big.png', { type: 'image/png' });
        const dt = new DataTransfer(); dt.items.add(big);
        document.querySelector('.ProseMirror').dispatchEvent(
          new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));""")
    time.sleep(0.4)
    mixed = [t.text for t in toasts(driver)]
    shot(driver, 'toasts_mixed')
    check('[toast] Different messages still stack (warning + size error both shown)',
          'You can attach up to 3 images' in mixed and 'Each image must be 5 MB or smaller' in mixed and len(mixed) == 2, mixed)
    time.sleep(4)
    check('[toast] All gone ~3s after the last one', len(toasts(driver)) == 0, len(toasts(driver)))
    driver.find_element(By.TAG_NAME, 'body').send_keys('\ue00c')  # Escape closes the dialog


def run_results_times(driver, headers, stamp):
    """Results table shows each candidate's start and submit date-time."""
    quiz_id = new_quiz(headers, f'Selenium results times {stamp}', 'exam')
    try:
        now = datetime.now(timezone.utc)
        requests.put(f'{API}/quizzes/{quiz_id}', headers=headers, json={
            'exam_start_at': (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'exam_end_at': (now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')}).raise_for_status()
        slug = requests.post(f'{API}/quizzes/{quiz_id}/publish-exam', headers=headers).json().get('exam_slug')
        # One candidate submits, one is left in progress
        done = requests.post(f'{API}/e/{slug}/start', json={'display_name': 'Finished Candidate'}).json()
        time.sleep(3)
        requests.post(f'{API}/e/{slug}/submit', json={'session_token': done['session_token']}).raise_for_status()
        requests.post(f'{API}/e/{slug}/start', json={'display_name': 'Busy Candidate'}).raise_for_status()

        api_rows = {r['display_name']: r for r in requests.get(f'{API}/quiz/{quiz_id}/exam-results', headers=headers).json()['leaderboard']}
        fin = api_rows.get('Finished Candidate', {})
        utc = lambda v: str(v or '').endswith(('Z', '+00:00'))
        check('[results] API returns started_at/completed_at marked as UTC',
              utc(fin.get('started_at')) and utc(fin.get('completed_at')), fin)

        # View as a host in India: times must be shifted to IST, not shown as raw UTC
        driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {'timezoneId': 'Asia/Kolkata'})
        driver.get(f'{BASE}/quiz/{quiz_id}/exam-results')
        time.sleep(6)
        headers_text = [h.text.strip() for h in driver.find_elements(By.CSS_SELECTOR, '.ant-table-thead th')]
        check('[results] Table has Started and Submitted columns', 'Started' in headers_text and 'Submitted' in headers_text, headers_text)
        rows = {r.text.split('\n')[0]: r.text for r in driver.find_elements(By.CSS_SELECTOR, '.ant-table-tbody tr') if r.text.strip()}
        shot(driver, 'results_times')
        fin_row = next((t for k, t in rows.items() if 'Finished Candidate' in t), '')
        busy_row = next((t for k, t in rows.items() if 'Busy Candidate' in t), '')
        print(f'{INFO} finished row: {fin_row!r}')
        check('[results] Finished candidate shows two date-times', fin_row.count(':') >= 4 and str(now.year) in fin_row, fin_row)
        check('[results] Busy candidate shows a start time and "In Progress"', 'In Progress' in busy_row and str(now.year) in busy_row, busy_row)
        ist_start = (datetime.fromisoformat(fin['started_at'].replace('Z', '+00:00')) + timedelta(hours=5, minutes=30)).strftime('%d %b %Y, %H:%M:%S')
        check('[results] Start time shown in the viewer\'s timezone (IST)', ist_start in fin_row, f'expected {ist_start}')
    finally:
        cleanup(headers, quiz_id)


def main():
    token = subprocess.check_output([PYTHON, TOKEN_SCRIPT, 'meetnishant@gmail.com'] + TOKEN_ENV_ARGS).decode().strip()
    headers = {'Authorization': f'Bearer {token}'}
    stamp = int(time.time())

    driver = None
    try:
        driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=webdriver.ChromeOptions())
        driver.set_window_size(1440, 900)

        def login():
            driver.get(BASE)
            driver.delete_all_cookies()
            driver.add_cookie({'name': 'access_token', 'value': token, 'domain': DOMAIN,
                               'path': '/', 'secure': True, 'httpOnly': True})

        login()
        run_results_times(driver, headers, stamp)
        if os.environ.get('ONLY_RESULTS'):
            return
        login()
        run_toast_and_dates(driver, headers, stamp)
        login()
        run_toast_mixed(driver)
        login()
        run_names(driver, headers, stamp, required=True)
        login()
        run_names(driver, headers, stamp, required=False)
    finally:
        if driver:
            driver.quit()

    print()
    if issues:
        print(f'{FAIL} {len(issues)} issue(s): {issues}')
        sys.exit(1)
    print(f'{PASS} All checks passed')


if __name__ == '__main__':
    main()

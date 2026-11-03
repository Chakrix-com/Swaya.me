"""
Selenium verification for the delete-question button on the QuizBuilder
left-rail question cards (draft activities only).

For a throwaway exam and a throwaway quiz (3 questions each, created via API):
  - Cancel on the confirm prompt deletes nothing
  - Deleting a question that is NOT open removes exactly that one
  - Deleting the question currently open in the editor closes the editor
  - Remaining questions are renumbered (UI + API order)
  - No JS errors / failed API calls
Exam only: once published, the button is gone and the API rejects deletes.

Run:
    backend/.venv/bin/python3 scripts/selenium_rail_delete_question_verify.py

Watch live at: http://www.swaya.me:7900 (noVNC — no password)
"""
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By

sys.path.insert(0, '/home/vinay/Swaya.me/scripts')
from selenium_utils import inject_error_collectors, collect_js_errors  # noqa: E402

WEBDRIVER_URL = 'http://localhost:4444'
# RAIL_DELETE_ENV=live targets www.swaya.me (throwaway data is created and cleaned up there)
LIVE = os.environ.get('RAIL_DELETE_ENV') == 'live'
COOKIE_DOMAIN = 'www.swaya.me' if LIVE else 'test.swaya.me'
TARGET_BASE = f'https://{COOKIE_DOMAIN}'
API = f'{TARGET_BASE}/api/v1'
TOKEN_ENV_ARGS = ['--env', '/www/wwwroot/swaya-live/backend/.env'] if LIVE else []
TOKEN_SCRIPT = '/home/vinay/Swaya.me/scripts/generate_selenium_token.py'
PYTHON = '/home/vinay/Swaya.me/backend/.venv/bin/python3'
SHOT_DIR = sys.argv[1] if len(sys.argv) > 1 else None

PASS = '\033[92m PASS\033[0m'
FAIL = '\033[91m FAIL\033[0m'
INFO = '\033[94m INFO\033[0m'

issues = []


def check(name, condition):
    print(f'{PASS if condition else FAIL} {name}')
    if not condition:
        issues.append(name)
    return condition


def shot(driver, name):
    if SHOT_DIR:
        driver.save_screenshot(f'{SHOT_DIR}/{name}.png')


def cards(driver):
    return driver.find_elements(By.CSS_SELECTOR, '.qb-q-card')


def card_for(driver, label):
    return next((c for c in cards(driver) if label in c.text), None)


def visible_button(driver, text):
    hits = [b for b in driver.find_elements(By.TAG_NAME, 'button') if b.is_displayed() and b.text.strip() == text]
    return hits[-1] if hits else None


def prompt_visible(driver):
    return any(e.is_displayed() for e in driver.find_elements(By.XPATH, "//*[contains(text(), 'Delete this question?')]"))


def api_questions(quiz_id, headers):
    qs = requests.get(f'{API}/quizzes/{quiz_id}', headers=headers).json().get('questions', [])
    return sorted(qs, key=lambda q: q['order'])


def run_for(driver, quiz_type, headers, stamp):
    tag = f'[{quiz_type}]'
    quiz_res = requests.post(f'{API}/quizzes/', json={'title': f'Selenium RailDelete {quiz_type} {stamp}', 'quiz_type': quiz_type}, headers=headers)
    if not check(f'{tag} Created throwaway activity via API', quiz_res.status_code in (200, 201)):
        print(quiz_res.text)
        return
    quiz_id = quiz_res.json()['id']
    try:
        ids = {}
        for label in ('KEEP', 'REMOVE', 'OPENED'):
            r = requests.post(f'{API}/quizzes/{quiz_id}/questions', headers=headers, json={
                'question_type': 'mcq', 'text': f'{label} question {stamp}',
                'options': ['A', 'B'], 'correct_answer_index': 0, 'points': 1,
            })
            if not check(f'{tag} Created {label} question via API', r.status_code in (200, 201)):
                print(r.text)
                return
            ids[label] = r.json()['id']

        driver.get(f'{TARGET_BASE}/quiz/{quiz_id}/edit')
        time.sleep(4)
        inject_error_collectors(driver)

        check(f'{tag} Rail shows 3 cards, each with a delete button',
              len(cards(driver)) == 3 and len(driver.find_elements(By.CSS_SELECTOR, '.qb-q-card .qb-q-delete-btn')) == 3)

        # 1. Cancel deletes nothing
        card_for(driver, 'REMOVE').find_element(By.CSS_SELECTOR, '.qb-q-delete-btn').click()
        time.sleep(0.8)
        check(f'{tag} Confirmation prompt shown', prompt_visible(driver))
        check(f'{tag} Clicking delete did not open the question editor',
              len(driver.find_elements(By.CSS_SELECTOR, '.qb-q-card--active')) == 0)
        shot(driver, f'{quiz_type}_1_confirm')
        visible_button(driver, 'Cancel').click()
        time.sleep(1)
        check(f'{tag} Cancel: prompt closed, 3 cards remain', not prompt_visible(driver) and len(cards(driver)) == 3)
        check(f'{tag} Cancel: API still has 3 questions', len(api_questions(quiz_id, headers)) == 3)

        # 2. Delete a question that is not open
        card_for(driver, 'REMOVE').find_element(By.CSS_SELECTOR, '.qb-q-delete-btn').click()
        time.sleep(0.8)
        visible_button(driver, 'Delete').click()
        time.sleep(2.5)
        check(f'{tag} Delete: REMOVE card gone, 2 remain', len(cards(driver)) == 2 and card_for(driver, 'REMOVE') is None)
        remaining = api_questions(quiz_id, headers)
        check(f'{tag} Delete: API has exactly KEEP + OPENED', [q['id'] for q in remaining] == [ids['KEEP'], ids['OPENED']])
        check(f'{tag} Delete: API order renumbered to 0..n-1 or 1..n',
              [q['order'] for q in remaining] in ([0, 1], [1, 2]))
        opened = card_for(driver, 'OPENED')
        check(f'{tag} Delete: OPENED card renumbered to Q2 in rail', opened is not None and 'Q2' in opened.text)

        # 3. Delete the question that is open in the editor
        card_for(driver, 'OPENED').click()
        time.sleep(1.5)
        check(f'{tag} OPENED question is open in editor',
              len(driver.find_elements(By.CSS_SELECTOR, '.qb-q-card--active')) == 1)
        shot(driver, f'{quiz_type}_2_editor_open')
        card_for(driver, 'OPENED').find_element(By.CSS_SELECTOR, '.qb-q-delete-btn').click()
        time.sleep(0.8)
        visible_button(driver, 'Delete').click()
        time.sleep(3)
        check(f'{tag} Delete-open: only KEEP card remains', len(cards(driver)) == 1 and card_for(driver, 'KEEP') is not None)
        check(f'{tag} Delete-open: editor closed, empty state shown',
              len(driver.find_elements(By.CSS_SELECTOR, '.qb-q-card--active')) == 0
              and len(driver.find_elements(By.CSS_SELECTOR, '.qb-stage-empty')) == 1)
        check(f'{tag} Delete-open: API has exactly KEEP', [q['id'] for q in api_questions(quiz_id, headers)] == [ids['KEEP']])
        shot(driver, f'{quiz_type}_3_after')
        time.sleep(2)  # let any stray debounced autosave fire before collecting errors
        errors, failed = collect_js_errors(driver, f'{quiz_type} rail delete')
        check(f'{tag} No JS errors or failed API calls', not errors and not failed)
        check(f'{tag} No error toast on screen', len(driver.find_elements(By.CSS_SELECTOR, '.ant-message-error')) == 0)

        # 4. Published exams stay locked
        if quiz_type == 'exam':
            now = datetime.now(timezone.utc)
            upd = requests.put(f'{API}/quizzes/{quiz_id}', headers=headers, json={
                'exam_start_at': (now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S'),
                'exam_end_at': (now + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%S'),
            })
            pub = requests.post(f'{API}/quizzes/{quiz_id}/publish-exam', headers=headers)
            if check(f'{tag} Published throwaway exam via API', upd.status_code == 200 and pub.status_code in (200, 201)):
                driver.get(f'{TARGET_BASE}/quiz/{quiz_id}/edit')
                time.sleep(4)
                check(f'{tag} Published: card visible, no delete button',
                      len(cards(driver)) == 1 and len(driver.find_elements(By.CSS_SELECTOR, '.qb-q-delete-btn')) == 0)
                shot(driver, f'{quiz_type}_4_published')
                rej = requests.delete(f'{API}/quizzes/questions/{ids["KEEP"]}', headers=headers)
                check(f'{tag} Published: API rejects delete (HTTP 400)', rej.status_code == 400)
                check(f'{tag} Published: question still there', len(api_questions(quiz_id, headers)) == 1)
            else:
                print(upd.status_code, upd.text[:300], pub.status_code, pub.text[:300])
    finally:
        if quiz_type == 'exam':
            requests.post(f'{API}/quizzes/{quiz_id}/unpublish-exam', headers=headers)
        d = requests.delete(f'{API}/quizzes/{quiz_id}', headers=headers)
        print(f'{INFO} {tag} Cleaned up throwaway activity {quiz_id} (HTTP {d.status_code})')


def main():
    token = subprocess.check_output([PYTHON, TOKEN_SCRIPT, 'meetnishant@gmail.com'] + TOKEN_ENV_ARGS).decode().strip()
    headers = {'Authorization': f'Bearer {token}'}
    stamp = int(time.time())

    driver = None
    try:
        driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=webdriver.ChromeOptions())
        driver.set_window_size(1440, 900)
        driver.get(TARGET_BASE)
        driver.delete_all_cookies()
        driver.add_cookie({'name': 'access_token', 'value': token, 'domain': COOKIE_DOMAIN,
                           'path': '/', 'secure': True, 'httpOnly': True})
        for quiz_type in ('exam', 'quiz'):
            run_for(driver, quiz_type, headers, stamp)
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

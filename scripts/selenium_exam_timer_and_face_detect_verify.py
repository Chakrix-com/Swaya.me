"""
Selenium verification on the candidate exam page (/e/{slug}) for:

  A. Per-question timer — switching questions must not hand back the full time,
     and an expired question must be locked (palette disabled).
  B. Webcam face detection — a blocked/empty camera view and a second person in
     view must each be logged as violations; a single visible face must not.

Camera scenarios feed Chrome a fake camera from a .y4m file that must already be
inside the selenium container (oneface, twofaces, scene, covered under /tmp).

Run (test env only — reads proctoring_events from the test DB):
    backend/.venv/bin/python3 scripts/selenium_exam_timer_and_face_detect_verify.py [timer|camera|all] [screenshot_dir]

Watch live at: http://www.swaya.me:7900 (noVNC — no password)
"""
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import pymysql
import requests
from dotenv import dotenv_values
from selenium import webdriver
from selenium.webdriver.common.by import By

# EXAM_ENV=live targets www.swaya.me (throwaway exams are created and cleaned up there;
# proctoring rows are only read). Live sends no camera-blocking header, so no proxy is needed.
LIVE = os.environ.get('EXAM_ENV') == 'live'
BASE = 'https://www.swaya.me' if LIVE else 'https://test.swaya.me'
API = f'{BASE}/api/v1'
# test.swaya.me's nginx sends Permissions-Policy: camera=() (live does not), so the
# camera scenarios need the same build served from an origin without that header.
# EXAM_UI_BASE=http://localhost:5199 points the browser at a static+API proxy
# running inside the selenium container (localhost is a secure context).
UI_BASE = os.environ.get('EXAM_UI_BASE', BASE)
WEBDRIVER_URL = 'http://localhost:4444'
TOKEN_SCRIPT = '/home/vinay/Swaya.me/scripts/generate_selenium_token.py'
PYTHON = '/home/vinay/Swaya.me/backend/.venv/bin/python3'
TEST_ENV = '/www/wwwroot/swaya-live/backend/.env' if LIVE else '/home/vinay/Swaya.me/backend/.env'
MODE = sys.argv[1] if len(sys.argv) > 1 else 'all'
SHOT_DIR = sys.argv[2] if len(sys.argv) > 2 else None

PASS = '\033[92m PASS\033[0m'
FAIL = '\033[91m FAIL\033[0m'
INFO = '\033[94m INFO\033[0m'
ALL_RULE_IDS = [
    'fullscreen_enforce', 'tab_switch_detect', 'copy_paste_block', 'multi_tab_detect',
    'right_click_block', 'bot_signal_detect', 'honeypot_traps', 'question_randomization',
    'option_randomization', 'answer_timing_enforce', 'behavioral_biometrics',
    'browser_fingerprint_bind', 'ip_bind', 'steg_watermark', 'devtools_detect',
    'webcam_monitoring', 'canvas_rendering',
]
issues = []


def check(name, condition, detail=''):
    print(f'{PASS if condition else FAIL} {name}{(" — " + str(detail)) if detail != "" else ""}')
    if not condition:
        issues.append(name)
    return condition


def shot(driver, name):
    if SHOT_DIR:
        driver.save_screenshot(f'{SHOT_DIR}/{name}.png')


def db_events(quiz_id):
    e = dotenv_values(TEST_ENV)
    c = pymysql.connect(host=e.get('DB_HOST', 'localhost'), port=int(e.get('DB_PORT', 3306)),
                        user=e['DB_USER'], password=e['DB_PASSWORD'], database=e['DB_NAME'])
    try:
        cur = c.cursor()
        cur.execute('select event_type, count(*) from proctoring_events where quiz_id=%s group by event_type', (quiz_id,))
        return dict(cur.fetchall())
    finally:
        c.close()


def db_session(quiz_id):
    """(is_locked, violation_count, integrity_score) of the newest proctoring session for the quiz."""
    e = dotenv_values(TEST_ENV)
    c = pymysql.connect(host=e.get('DB_HOST', 'localhost'), port=int(e.get('DB_PORT', 3306)),
                        user=e['DB_USER'], password=e['DB_PASSWORD'], database=e['DB_NAME'])
    try:
        cur = c.cursor()
        cur.execute('select is_locked, violation_count, integrity_score from proctoring_sessions where quiz_id=%s order by id desc limit 1', (quiz_id,))
        return cur.fetchone()
    finally:
        c.close()


def make_exam(headers, title, question_times, policy=None):
    r = requests.post(f'{API}/quizzes/', json={'title': title, 'quiz_type': 'exam'}, headers=headers)
    r.raise_for_status()
    quiz_id = r.json()['id']
    for i, secs in enumerate(question_times):
        body = {'question_type': 'mcq', 'text': f'Question {i + 1}', 'options': ['A', 'B'],
                'correct_answer_index': 0, 'points': 1}
        if secs:
            body['max_time_seconds'] = secs
        requests.post(f'{API}/quizzes/{quiz_id}/questions', headers=headers, json=body).raise_for_status()
    now = datetime.now(timezone.utc)
    upd = {'exam_start_at': (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
           'exam_end_at': (now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')}
    if policy:
        upd['proctoring_policy'] = policy
    u = requests.put(f'{API}/quizzes/{quiz_id}', headers=headers, json=upd)
    if u.status_code != 200:
        print(u.status_code, u.text[:300])
    pub = requests.post(f'{API}/quizzes/{quiz_id}/publish-exam', headers=headers)
    if pub.status_code not in (200, 201):
        print(pub.status_code, pub.text[:300])
        cleanup(headers, quiz_id)
        raise SystemExit('could not publish throwaway exam')
    slug = pub.json().get('exam_slug') or requests.get(f'{API}/quizzes/{quiz_id}', headers=headers).json().get('exam_slug')
    return quiz_id, slug


def cleanup(headers, quiz_id):
    requests.post(f'{API}/quizzes/{quiz_id}/unpublish-exam', headers=headers)
    d = requests.delete(f'{API}/quizzes/{quiz_id}', headers=headers)
    print(f'{INFO} Cleaned up throwaway exam {quiz_id} (HTTP {d.status_code})')


def new_driver(fake_video=None):
    opts = webdriver.ChromeOptions()
    if fake_video:
        opts.add_argument('--use-fake-ui-for-media-stream')
        opts.add_argument('--use-fake-device-for-media-stream')
        opts.add_argument(f'--use-file-for-fake-video-capture={fake_video}')
        # The grid's Chromium has no GPU; mediapipe needs WebGL to read video frames
        opts.add_argument('--use-angle=swiftshader')
        opts.add_argument('--ignore-gpu-blocklist')
    d = webdriver.Remote(command_executor=WEBDRIVER_URL, options=opts)
    d.set_window_size(1440, 900)
    return d


def click_button(driver, text, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        for b in driver.find_elements(By.TAG_NAME, 'button'):
            try:
                if b.is_displayed() and b.is_enabled() and text.lower() in b.text.strip().lower():
                    b.click()
                    return True
            except Exception:
                pass
        time.sleep(0.4)
    return False


def start_exam(driver, slug, has_proctoring):
    driver.get(f'{UI_BASE}/e/{slug}')
    time.sleep(4)
    driver.find_element(By.CSS_SELECTOR, 'input#display_name, input[placeholder]').send_keys('Selenium Candidate')
    if has_proctoring:
        driver.find_element(By.ID, 'proctor-ack').click()
    return click_button(driver, 'Start')


def q_timer(driver):
    """Seconds shown on the per-question timer tag, or None if no tag."""
    for el in driver.find_elements(By.CSS_SELECTOR, '.ant-tag'):
        m = re.search(r'Question Time:\s*(\d+):(\d+)', el.text)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))
    return None


def palette_btn(driver, n):
    return next(b for b in driver.find_elements(By.CSS_SELECTOR, 'nav button') if b.text.strip() == str(n))


def current_q(driver):
    b = next((b for b in driver.find_elements(By.CSS_SELECTOR, 'nav button') if b.get_attribute('aria-current') == 'true'), None)
    return int(b.text.strip()) if b else None


def run_timer(headers, stamp):
    quiz_id, slug = make_exam(headers, f'Selenium Timer {stamp}', [40, 6, 40])
    driver = None
    try:
        driver = new_driver()
        check('[timer] Exam started', start_exam(driver, slug, False))
        time.sleep(2)
        t0 = q_timer(driver)
        check('[timer] Q1 timer starts near 40s', t0 is not None and 36 <= t0 <= 40, t0)
        time.sleep(8)
        before = q_timer(driver)
        palette_btn(driver, 3).click()
        time.sleep(4)
        check('[timer] Now on Q3 with its own full timer', current_q(driver) == 3 and (q_timer(driver) or 0) >= 34, q_timer(driver))
        palette_btn(driver, 1).click()
        time.sleep(1)
        after = q_timer(driver)
        shot(driver, 'timer_back_on_q1')
        check('[timer] Back on Q1: timer resumed, NOT reset to 40', after is not None and before - 3 <= after <= before, f'before={before} after={after}')

        # Rapid flipping must not gain time
        for _ in range(5):
            palette_btn(driver, 3).click(); time.sleep(0.3)
            palette_btn(driver, 1).click(); time.sleep(0.3)
        flip = q_timer(driver)
        check('[timer] Rapid switching does not add time back', flip is not None and flip <= after, f'{after} -> {flip}')

        # Expiry: Q2 has 6s
        palette_btn(driver, 2).click()
        time.sleep(1)
        driver.find_elements(By.CSS_SELECTOR, '.ant-radio-input, input[type=radio]')[0].click()
        time.sleep(8)
        shot(driver, 'timer_q2_expired')
        check('[timer] Q2 expired: auto-advanced to Q3', current_q(driver) == 3, current_q(driver))
        check('[timer] Q2 palette button is disabled', not palette_btn(driver, 2).is_enabled())
        q3 = q_timer(driver)
        check('[timer] Q3 timer resumed from earlier visit, not reset', q3 is not None and q3 <= 36, q3)
        palette_btn(driver, 2).click() if palette_btn(driver, 2).is_enabled() else None
        check('[timer] Cannot navigate back to expired Q2', current_q(driver) == 3)
    finally:
        if driver:
            driver.quit()
        cleanup(headers, quiz_id)


def camera_exam(headers, title, question_times, lock_at):
    rules = {rid: {'enabled': rid == 'webcam_monitoring'} for rid in ALL_RULE_IDS}
    policy = {'enabled': True, 'rules': rules, 'escalation': {'lock_on_violation_count': lock_at, 'auto_submit_on_lock': True}}
    return make_exam(headers, title, question_times, policy)


def body_text(driver):
    return driver.find_element(By.TAG_NAME, 'body').text


def run_identity_blocked(headers, stamp, name, video, expect_text):
    """Identity step must refuse a covered lens / empty frame / second person."""
    quiz_id, slug = camera_exam(headers, f'Selenium Identity {name} {stamp}', [None], 20)
    tag = f'[identity:{name}]'
    driver = None
    try:
        driver = new_driver(video)
        check(f'{tag} Start screen submitted', start_exam(driver, slug, True))
        check(f'{tag} Capture clicked', click_button(driver, 'Capture', 30))
        time.sleep(4)
        txt = body_text(driver)
        shot(driver, f'identity_{name}')
        check(f'{tag} Error shown: "{expect_text}"', expect_text.lower() in txt.lower(), txt[-200:].replace('\n', ' | '))
        check(f'{tag} NOT verified, no Start Exam button', 'Identity verified' not in txt and 'Start Exam' not in txt)
        # A second attempt with the same view is refused too
        click_button(driver, 'Capture', 5)
        time.sleep(4)
        check(f'{tag} Still blocked on retry', 'Identity verified' not in body_text(driver))
    finally:
        if driver:
            driver.quit()
        cleanup(headers, quiz_id)


LIVE_FEED = '/tmp/live.y4m'


def set_feed(src):
    """Swap what the fake camera shows by overwriting the looping .y4m in place
    (same size, no truncation), so the view can change mid-exam like a real one."""
    subprocess.check_call(['sudo', 'docker', 'exec', '-u', 'root', 'selenium-arm', 'dd', f'if={src}',
                           f'of={LIVE_FEED}', 'conv=notrunc', 'status=none'])


def run_camera(headers, stamp, name, video, expect, lock_at=20, watch_secs=22):
    # Q1 carries a 40s question timer so the "timer waits for Start Exam" check runs here too
    quiz_id, slug = camera_exam(headers, f'Selenium Camera {name} {stamp}', [40, None], lock_at)
    tag = f'[camera:{name}]'
    driver = None
    try:
        # Identity is always passed with one visible face; the view changes afterwards
        set_feed('/tmp/oneface.y4m')
        driver = new_driver(LIVE_FEED)
        check(f'{tag} Start screen submitted', start_exam(driver, slug, True))
        check(f'{tag} Identity photo captured', click_button(driver, 'Capture', 30))
        time.sleep(4)
        check(f'{tag} Identity verified with one visible face', 'Identity verified' in body_text(driver))
        if expect == 'none':
            # Sit on the "Start Exam" screen: the question clock must not run behind it
            time.sleep(12)
            check(f'{tag} Question palette hidden before Start Exam', not driver.find_elements(By.CSS_SELECTOR, 'nav button'))
            shot(driver, 'identity_verified_waiting')
        check(f'{tag} Entered exam after identity step', click_button(driver, 'Start', 15))
        time.sleep(2)
        check(f'{tag} Exam question visible', 'Question 1' in body_text(driver))
        set_feed(video)
        if expect == 'none':
            t0 = q_timer(driver)
            check(f'{tag} Q1 timer starts near 40s only after Start Exam (waited 12s first)', t0 is not None and t0 >= 36, t0)
        # The warning overlay auto-dismisses after a few seconds, so watch for it while waiting
        saw_warning = False
        overlay_text = ''
        end = time.time() + watch_secs
        while time.time() < end:
            if not saw_warning and 'Proctoring Violation' in body_text(driver):
                saw_warning = True
                overlay_text = body_text(driver)
                shot(driver, f'camera_{name}_warning')
            time.sleep(0.5)
        shot(driver, f'camera_{name}')
        ev = db_events(quiz_id)
        print(f'{INFO} {tag} events after ~{watch_secs + 3}s: {ev}')
        absent, multi = ev.get('FACE_NOT_DETECTED', 0), ev.get('MULTIPLE_FACES_DETECTED', 0)
        if expect == 'none':
            check(f'{tag} No face violations for a single visible face', absent == 0 and multi == 0, ev)
        elif expect == 'absent':
            check(f'{tag} FACE_NOT_DETECTED logged', absent >= 1, absent)
            check(f'{tag} ...but not spammed (cooldown holds)', absent <= 1 + watch_secs // 15, absent)
            check(f'{tag} No false multiple-face event', multi == 0, multi)
        elif expect == 'multi':
            check(f'{tag} MULTIPLE_FACES_DETECTED logged', multi >= 1, multi)
            check(f'{tag} ...but not spammed (cooldown holds)', multi <= 1 + watch_secs // 15, multi)
            check(f'{tag} No false face-absent event', absent == 0, absent)
        if expect != 'none':
            # Face events are warn-only: logged + warned, never counted toward the lock
            sess = db_session(quiz_id)
            check(f'{tag} Session NOT locked by face events (lock limit {lock_at})', sess is not None and sess[0] == 0, sess)
            check(f'{tag} violation_count untouched, integrity score reduced', sess is not None and sess[1] == 0 and sess[2] < 100, sess)
            check(f'{tag} Exam still usable (question visible, no lock screen)', 'Question' in body_text(driver))
            check(f'{tag} Warning does not claim violations were used up', 'remaining before lock' not in overlay_text, overlay_text[-160:].replace('\n', ' | '))
        check(f'{tag} Candidate warning overlay ' + ('not shown' if expect == 'none' else 'shown'), saw_warning == (expect != 'none'))
    finally:
        if driver:
            driver.quit()
        cleanup(headers, quiz_id)


def main():
    token = subprocess.check_output([PYTHON, TOKEN_SCRIPT, 'meetnishant@gmail.com'] + (['--env', TEST_ENV] if LIVE else [])).decode().strip()
    headers = {'Authorization': f'Bearer {token}'}
    stamp = int(time.time())
    if MODE in ('timer', 'all'):
        run_timer(headers, stamp)
    if MODE in ('identity', 'all'):
        run_identity_blocked(headers, stamp, 'covered', '/tmp/covered.y4m', 'blocked or too dark')
        run_identity_blocked(headers, stamp, 'emptyroom', '/tmp/scene.y4m', 'No face detected')
        run_identity_blocked(headers, stamp, 'twofaces', '/tmp/twofaces.y4m', 'More than one face')
    if MODE in ('camera', 'all'):
        run_camera(headers, stamp, 'oneface', '/tmp/oneface.y4m', 'none')
        # lock limit 1: a single counted violation would lock + auto-submit immediately
        run_camera(headers, stamp, 'covered', '/tmp/covered.y4m', 'absent', lock_at=1, watch_secs=40)
        run_camera(headers, stamp, 'emptyroom', '/tmp/scene.y4m', 'absent', lock_at=1, watch_secs=40)
        run_camera(headers, stamp, 'twofaces', '/tmp/twofaces.y4m', 'multi', lock_at=1)
    print()
    if issues:
        print(f'{FAIL} {len(issues)} issue(s): {issues}')
        sys.exit(1)
    print(f'{PASS} All checks passed')


if __name__ == '__main__':
    main()

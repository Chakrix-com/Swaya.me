"""
Selenium verification: screenshots attached to the global feedback bubble.

  - "Attach screenshot" file picker and Ctrl+V paste both add thumbnails
  - Removing a thumbnail works; a 4th image is refused (max 3)
  - Submit stores the feedback with its screenshots (re-encoded PNG)
  - Super admin sees thumbnails in Admin → Feedback → App Feedback and they load
  - Attachment URLs refuse anonymous requests; non-image uploads are rejected
    and leave no feedback row behind
  - Plain feedback without screenshots still goes through the old endpoint

Run:
    backend/.venv/bin/python3 scripts/selenium_feedback_screenshot_verify.py [shot_dir]
    FEEDBACK_ENV=live ...   # against www.swaya.me; created rows/files are removed after

Watch live at: http://www.swaya.me:7900 (noVNC — no password)
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pymysql
import requests
from dotenv import dotenv_values
from selenium import webdriver
from selenium.webdriver.common.by import By

LIVE = os.environ.get('FEEDBACK_ENV') == 'live'
DOMAIN = 'www.swaya.me' if LIVE else 'test.swaya.me'
BASE = f'https://{DOMAIN}'
API = f'{BASE}/api/v1'
WEBDRIVER_URL = 'http://localhost:4444'
TOKEN_SCRIPT = '/home/vinay/Swaya.me/scripts/generate_selenium_token.py'
PYTHON = '/home/vinay/Swaya.me/backend/.venv/bin/python3'
BACKEND_DIR = '/www/wwwroot/swaya-live/backend' if LIVE else '/home/vinay/Swaya.me/backend'
ENV_FILE = f'{BACKEND_DIR}/.env'
SHOT_DIR = sys.argv[1] if len(sys.argv) > 1 else None
CONTAINER_IMG = '/tmp/feedback_shot.png'
MARKER = f'Selenium screenshot feedback {int(time.time())}'

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


def db():
    e = dotenv_values(ENV_FILE)
    return pymysql.connect(host=e.get('DB_HOST', 'localhost'), port=int(e.get('DB_PORT', 3306)),
                           user=e['DB_USER'], password=e['DB_PASSWORD'], database=e['DB_NAME'])


def rows_like(text):
    c = db()
    try:
        cur = c.cursor()
        cur.execute('select id, attachments from app_feedback where feedback_text like %s', (f'%{text}%',))
        return cur.fetchall()
    finally:
        c.close()


def cleanup(text):
    """Remove the feedback rows (and their screenshot folders) this run created."""
    uploads = dotenv_values(ENV_FILE).get('UPLOADS_BASE_DIR') or './uploads'
    base = Path(uploads) if os.path.isabs(uploads) else Path(BACKEND_DIR) / uploads
    c = db()
    try:
        cur = c.cursor()
        cur.execute('select id from app_feedback where feedback_text like %s', (f'%{text}%',))
        ids = [r[0] for r in cur.fetchall()]
        for fid in ids:
            shutil.rmtree(base / 'feedback' / str(fid), ignore_errors=True)
        if ids:
            cur.execute(f'delete from app_feedback where id in ({",".join(["%s"] * len(ids))})', ids)
            c.commit()
        print(f'{INFO} Cleaned up feedback rows {ids}')
    finally:
        c.close()


def open_feedback(driver):
    driver.find_element(By.CSS_SELECTOR, '.ant-float-btn').click()
    time.sleep(1.5)


def thumbs(driver):
    return driver.find_elements(By.CSS_SELECTOR, '.app-feedback-thumb')


def type_feedback(driver, text):
    ed = driver.find_element(By.CSS_SELECTOR, '.ProseMirror')
    ed.click()
    ed.send_keys(text)


def paste_image(driver, color):
    """Fire a real paste event carrying a PNG, as Ctrl+V of a screenshot would."""
    driver.execute_async_script("""
        const color = arguments[0];
        const done = arguments[arguments.length - 1];
        const c = document.createElement('canvas'); c.width = 320; c.height = 200;
        const g = c.getContext('2d'); g.fillStyle = color; g.fillRect(0, 0, 320, 200);
        g.fillStyle = '#fff'; g.font = '24px sans-serif'; g.fillText('pasted ' + color, 20, 100);
        c.toBlob((blob) => {
          const dt = new DataTransfer();
          dt.items.add(new File([blob], 'pasted.png', { type: 'image/png' }));
          document.querySelector('.ProseMirror').dispatchEvent(
            new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
          done();
        }, 'image/png');
    """, color)
    time.sleep(0.6)


def main():
    # A real screenshot-like PNG inside the selenium container for the file picker
    from PIL import Image, ImageDraw
    local_png = '/tmp/claude_feedback_shot.png' if not SHOT_DIR else f'{SHOT_DIR}/upload_source.png'
    im = Image.new('RGB', (1280, 720), (30, 60, 120))
    ImageDraw.Draw(im).text((40, 40), 'Selenium feedback screenshot', fill='white')
    im.save(local_png)
    subprocess.check_call(['sudo', 'docker', 'cp', local_png, f'selenium-arm:{CONTAINER_IMG}'])

    token = subprocess.check_output([PYTHON, TOKEN_SCRIPT, 'meetnishant@gmail.com'] + (['--env', ENV_FILE] if LIVE else [])).decode().strip()
    headers = {'Authorization': f'Bearer {token}'}

    driver = None
    try:
        driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=webdriver.ChromeOptions())
        driver.set_window_size(1440, 900)
        driver.set_script_timeout(15)
        driver.get(BASE)
        driver.delete_all_cookies()
        driver.add_cookie({'name': 'access_token', 'value': token, 'domain': DOMAIN, 'path': '/', 'secure': True, 'httpOnly': True})
        driver.get(f'{BASE}/dashboard')
        time.sleep(5)

        # ── Submit with screenshots ──
        open_feedback(driver)
        check('Feedback dialog has an "Attach screenshot" button', any('Attach screenshot' in b.text for b in driver.find_elements(By.TAG_NAME, 'button')))
        type_feedback(driver, f'{MARKER} with screenshots')
        driver.find_element(By.CSS_SELECTOR, '.app-feedback-attachments input[type=file]').send_keys(CONTAINER_IMG)
        time.sleep(0.8)
        check('File picker adds a thumbnail', len(thumbs(driver)) == 1, len(thumbs(driver)))
        paste_image(driver, '#c0392b')
        check('Ctrl+V paste of an image adds a thumbnail', len(thumbs(driver)) == 2, len(thumbs(driver)))
        editor_imgs = driver.find_elements(By.CSS_SELECTOR, '.ProseMirror img')
        check('Pasted image did not land inside the text editor', len(editor_imgs) == 0, len(editor_imgs))
        paste_image(driver, '#27ae60')
        paste_image(driver, '#8e44ad')
        check('A 4th image is refused (max 3)', len(thumbs(driver)) == 3, len(thumbs(driver)))
        thumbs(driver)[1].find_element(By.TAG_NAME, 'button').click()
        time.sleep(0.4)
        check('Removing a thumbnail works', len(thumbs(driver)) == 2, len(thumbs(driver)))
        shot(driver, 'feedback_dialog_with_screenshots')
        next(b for b in driver.find_elements(By.TAG_NAME, 'button') if b.text.strip() == 'Submit Feedback').click()
        time.sleep(3)
        body = driver.find_element(By.TAG_NAME, 'body').text
        check('Success message shown', 'Thank you for your feedback' in body)

        rows = rows_like(f'{MARKER} with screenshots')
        stored = json.loads(rows[0][1]) if len(rows) == 1 and rows[0][1] else []
        check('Feedback row stored with 2 attachments', len(stored) == 2, rows)

        # ── API protections ──
        lst = requests.get(f'{API}/admin/app-feedback', headers=headers, params={'search': MARKER}).json()
        item = next((i for i in lst.get('items', []) if 'with screenshots' in i['feedback_text']), None)
        urls = (item or {}).get('attachment_urls', [])
        check('Admin API lists 2 attachment URLs', len(urls) == 2, urls)
        if urls:
            r = requests.get(f'{BASE}{urls[0]}', headers=headers)
            check('Super admin can fetch a screenshot (PNG)', r.status_code == 200 and r.content.startswith(b'\x89PNG'), r.status_code)
            anon = requests.get(f'{BASE}{urls[0]}')
            check('Anonymous request for a screenshot is refused', anon.status_code in (401, 403), anon.status_code)
            name = urls[0].rsplit('/', 1)[1]
            pub = requests.get(f'{BASE}/api/uploads/images/feedback/{item["id"]}/{name}')
            check('Screenshot is not reachable via the public uploads path', pub.status_code != 200 or not pub.content.startswith(b'\x89PNG'), pub.status_code)

        bad = requests.post(f'{API}/feedback/app/with-attachments',
                            data={'payload': f'{{"page_url": "{BASE}/x", "feedback_text": "{MARKER} bad upload"}}'},
                            files=[('files', ('evil.png', b'<script>alert(1)</script>', 'image/png'))])
        check('Non-image upload rejected with 400', bad.status_code == 400, f'{bad.status_code} {bad.text[:80]}')
        check('...and no feedback row was created for it', len(rows_like(f'{MARKER} bad upload')) == 0)

        # ── Admin UI ──
        driver.get(f'{BASE}/admin/feedback')
        time.sleep(4)
        next(t for t in driver.find_elements(By.CSS_SELECTOR, '.ant-tabs-tab') if 'App Feedback' in t.text).click()
        time.sleep(3)
        imgs = driver.find_elements(By.CSS_SELECTOR, '.app-feedback-admin-thumbs img')
        loaded = [i for i in imgs if driver.execute_script('return arguments[0].complete && arguments[0].naturalWidth > 0', i)]
        shot(driver, 'admin_feedback_thumbnails')
        check('Admin feedback table shows loaded screenshot thumbnails', len(loaded) >= 2, f'{len(loaded)}/{len(imgs)}')

        # ── Plain feedback still works ──
        driver.get(f'{BASE}/dashboard')
        time.sleep(4)
        open_feedback(driver)
        type_feedback(driver, f'{MARKER} text only')
        next(b for b in driver.find_elements(By.TAG_NAME, 'button') if b.text.strip() == 'Submit Feedback').click()
        time.sleep(3)
        plain = rows_like(f'{MARKER} text only')
        check('Text-only feedback still submits (no attachments)', len(plain) == 1 and not plain[0][1], plain)
    finally:
        if driver:
            driver.quit()
        cleanup(MARKER)
        subprocess.call(['sudo', 'docker', 'exec', '-u', 'root', 'selenium-arm', 'rm', '-f', CONTAINER_IMG])

    print()
    if issues:
        print(f'{FAIL} {len(issues)} issue(s): {issues}')
        sys.exit(1)
    print(f'{PASS} All checks passed')


if __name__ == '__main__':
    main()

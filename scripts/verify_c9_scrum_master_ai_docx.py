"""
Selenium end-to-end verify: create the "C9 Scrum Master" exam via the UI as
demo@swaya.me (real login form, not token injection), add one question by
hand, then use "Generate with AI" -> Upload file (Word doc) -> restrict types
to MCQ + Multi-Select MCQ (Code unchecked) -> generate -> add questions.

Run:
    /home/vinay/Swaya.me/backend/.venv/bin/python3 scripts/verify_c9_scrum_master_ai_docx.py
"""
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.insert(0, '/home/vinay/Swaya.me/scripts')
from selenium_utils import inject_error_collectors, collect_js_errors  # noqa: E402

WEBDRIVER_URL = 'http://localhost:4444'
TARGET_BASE = 'https://test.swaya.me'
DOCX_PATH = '/tmp/claude-1005/-home-vinay-Swaya-me/e6372092-24c1-463a-96ef-7f243c36c5f0/scratchpad/c9_scrum_master_study_guide.docx'
SHOT_DIR = '/tmp/claude-1005/-home-vinay-Swaya-me/e6372092-24c1-463a-96ef-7f243c36c5f0/scratchpad'

PASS = '\033[92m PASS\033[0m'
FAIL = '\033[91m FAIL\033[0m'
INFO = '\033[94m INFO\033[0m'
issues = []


def check(name, cond):
    print((PASS if cond else FAIL) + ' ' + name)
    if not cond:
        issues.append(name)
    return cond


def wait_for(driver, by, value, timeout=15, visible=True):
    try:
        cond = EC.visibility_of_element_located((by, value)) if visible else EC.presence_of_element_located((by, value))
        return WebDriverWait(driver, timeout).until(cond)
    except Exception:
        return None


def js_click(driver, el):
    driver.execute_script('arguments[0].click();', el)


def main():
    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1440,1400')
    driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=options)
    driver.set_page_load_timeout(30)

    try:
        # ── 1. Real login as demo@swaya.me ──────────────────────────────────
        driver.get(f'{TARGET_BASE}/login')
        time.sleep(2)
        inject_error_collectors(driver)

        email_input = wait_for(driver, By.CSS_SELECTOR, '#login_email', timeout=15) \
            or wait_for(driver, By.CSS_SELECTOR, 'input[type="email"]', timeout=10)
        check('Login email field found', email_input is not None)
        email_input.send_keys('demo@swaya.me')

        password_input = wait_for(driver, By.CSS_SELECTOR, '#login_password', timeout=10) \
            or wait_for(driver, By.CSS_SELECTOR, 'input[type="password"]', timeout=10)
        check('Login password field found', password_input is not None)
        password_input.send_keys('Demo1234')

        submit = None
        for b in driver.find_elements(By.CSS_SELECTOR, "button[type='submit']"):
            if b.is_displayed():
                submit = b
                break
        check('Login submit button found', submit is not None)
        js_click(driver, submit)
        time.sleep(3)

        check(
            'Logged in (redirected away from /login)',
            '/login' not in driver.current_url,
        )
        print(f'{INFO} post-login URL: {driver.current_url}')
        driver.save_screenshot(f'{SHOT_DIR}/c9_01_logged_in.png')

        # ── 2. Create the exam via the UI ───────────────────────────────────
        driver.get(f'{TARGET_BASE}/quiz/new?type=exam')
        time.sleep(2)
        title_input = wait_for(driver, By.ID, 'title', timeout=15)
        check('Exam title input found', title_input is not None)
        title_input.send_keys('C9 Scrum Master')

        submit_btn = wait_for(driver, By.CSS_SELECTOR, 'button[type="submit"]', timeout=10)
        check('Create-exam submit button found', submit_btn is not None)
        js_click(driver, submit_btn)

        WebDriverWait(driver, 20).until(EC.url_contains('/edit'))
        time.sleep(2)
        quiz_id = driver.current_url.rstrip('/').split('/')[-2]
        print(f'{INFO} quiz_id={quiz_id}, url={driver.current_url}')
        driver.save_screenshot(f'{SHOT_DIR}/c9_02_exam_created.png')

        # ── 3. Add one question by hand via the UI ──────────────────────────
        for b in driver.find_elements(By.XPATH, "//button[contains(., 'Add Question')]"):
            if b.is_displayed():
                js_click(driver, b)
                break
        time.sleep(1.5)

        ta = wait_for(driver, By.CSS_SELECTOR, 'textarea', timeout=10)
        check('Question text area found', ta is not None)
        ta.send_keys('Who participates in the Daily Scrum?')

        inputs = driver.find_elements(By.CSS_SELECTOR, '.qb-opt-content input.ant-input')
        check('4 default option fields present', len(inputs) >= 2)
        values = ['Only the Developers', 'The entire Scrum Team', 'Only the Scrum Master', 'Stakeholders']
        for i, v in enumerate(values[:len(inputs)]):
            inputs[i].send_keys(v)

        dots = driver.find_elements(By.CSS_SELECTOR, '.qb-opt-dot')
        js_click(driver, dots[0])  # "Only the Developers" is correct
        time.sleep(0.3)

        save_btn = None
        for b in driver.find_elements(By.XPATH, "//button[@type='submit']"):
            if b.is_displayed():
                save_btn = b
        check('Save-question button found', save_btn is not None)
        driver.execute_script('arguments[0].scrollIntoView(true);', save_btn)
        js_click(driver, save_btn)
        time.sleep(2)
        driver.save_screenshot(f'{SHOT_DIR}/c9_03_question_added_manually.png')

        body_text = driver.find_element(By.TAG_NAME, 'body').text
        check('Manually-added question visible in question list', 'Daily Scrum' in body_text)

        # ── 4. Generate with AI — Upload file (Word doc) ─────────────────────
        for b in driver.find_elements(By.XPATH, "//button[contains(., 'Generate with AI')]"):
            if b.is_displayed():
                js_click(driver, b)
                break
        time.sleep(1.5)

        for tab in driver.find_elements(By.CSS_SELECTOR, '.ant-segmented-item'):
            if 'file' in tab.text.lower() or 'Upload' in tab.text:
                js_click(driver, tab)
                break
        time.sleep(1)

        file_input = wait_for(driver, By.CSS_SELECTOR, 'input[type="file"]', timeout=10, visible=False)
        check('File upload input found', file_input is not None)
        file_input.send_keys(DOCX_PATH)
        print(f'{INFO} uploaded {DOCX_PATH}')

        # Wait for extraction to complete (spinner disappears, textarea fills)
        extracted_ta = None
        for _ in range(30):
            time.sleep(1)
            areas = driver.find_elements(By.CSS_SELECTOR, 'textarea')
            for a in areas:
                val = a.get_attribute('value') or ''
                if len(val) > 200:
                    extracted_ta = a
                    break
            if extracted_ta:
                break
        check('Word doc text extracted into prompt', extracted_ta is not None)
        if extracted_ta:
            print(f'{INFO} extracted text length: {len(extracted_ta.get_attribute("value"))}')
        driver.save_screenshot(f'{SHOT_DIR}/c9_04_docx_extracted.png')

        # ── 5. Restrict question types — uncheck Code ────────────────────────
        checkboxes = driver.find_elements(By.CSS_SELECTOR, '.ant-checkbox-group .ant-checkbox-wrapper')
        labels = [c.text for c in checkboxes]
        print(f'{INFO} type checkboxes: {labels}')
        check('Question-type picker shows 4 options for exam', len(checkboxes) == 4)
        for c in checkboxes:
            if c.text.strip() == 'Code':
                code_input = c.find_element(By.CSS_SELECTOR, 'input')
                js_click(driver, code_input)
                break
        time.sleep(0.3)
        checkboxes_after = driver.find_elements(By.CSS_SELECTOR, '.ant-checkbox-group .ant-checkbox-wrapper')
        code_still_checked = any(
            c.text.strip() == 'Code' and 'ant-checkbox-checked' in c.get_attribute('innerHTML')
            for c in checkboxes_after
        )
        check('Code unchecked in type picker', not code_still_checked)

        # ── 6. Generate ───────────────────────────────────────────────────────
        # Match on EXACT text "Generate" — "contains" would also match the
        # "Generate with AI" trigger button sitting behind the modal overlay.
        gen_btn = None
        for b in driver.find_elements(By.TAG_NAME, 'button'):
            if b.is_displayed() and b.text.strip() == 'Generate':
                gen_btn = b
                break
        check('Generate button found', gen_btn is not None)
        js_click(driver, gen_btn)
        time.sleep(2)

        # Wait for the modal to leave the input step: the type-picker checkboxes
        # and the Difficulty radio group (input-step-only controls) disappear
        # once we're in the preview step.
        settled = False
        for _ in range(60):
            time.sleep(2)
            input_step_marker = driver.find_elements(By.CSS_SELECTOR, '.ant-checkbox-group')
            preview_cards = driver.find_elements(By.CSS_SELECTOR, '.ant-modal .ant-card')
            if not input_step_marker and len(preview_cards) > 0:
                settled = True
                break
        check('Left the input step after clicking Generate', settled)
        time.sleep(3)  # let the tail end of the stream settle
        driver.save_screenshot(f'{SHOT_DIR}/c9_05_ai_preview.png')

        page_text = driver.find_element(By.TAG_NAME, 'body').text
        check('No AI generation error shown', 'failed' not in page_text.lower() and 'unavailable' not in page_text.lower())

        type_tags = [t.text for t in driver.find_elements(By.CSS_SELECTOR, '.ant-tag')]
        print(f'{INFO} preview type tags: {type_tags}')
        check('No Code questions in preview (excluded type)', 'Code' not in type_tags)
        check('Multi-Select MCQ appears in AI preview', any('Multi-Select' in t for t in type_tags))

        js_errors, failed_fetches = collect_js_errors(driver)
        check('No JS console errors during AI generation', len(js_errors) == 0)
        if js_errors:
            print(f'{INFO} JS errors: {js_errors}')

        # ── 7. Add the generated questions ──────────────────────────────────
        # "Add {{count}} questions to quiz" — matching on "to quiz" avoids the
        # "Add Question" button sitting behind the modal.
        add_selected_btn = None
        for b in driver.find_elements(By.TAG_NAME, 'button'):
            if b.is_displayed() and 'to quiz' in b.text.lower():
                add_selected_btn = b
                break
        check('Add-selected-questions button found', add_selected_btn is not None)
        if add_selected_btn:
            print(f'{INFO} add button text: {add_selected_btn.text!r}')
            js_click(driver, add_selected_btn)
        time.sleep(4)
        driver.save_screenshot(f'{SHOT_DIR}/c9_06_questions_added.png')

    finally:
        driver.quit()

    print()
    if issues:
        print(f'{FAIL} {len(issues)} issue(s): {issues}')
        sys.exit(1)
    print(f'{PASS} All checks passed')


if __name__ == '__main__':
    main()

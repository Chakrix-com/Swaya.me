"""
Selenium visual verify: mcq_multi question type in the QuizBuilder.

Flow:
  1. Log in as meetnishant@gmail.com via injected JWT cookie
  2. Create a new EXAM (mcq_multi is only allowed for exam/offline_poll)
  3. Add a question, switch type to "Multi-Select MCQ"
  4. Fill 4 options, mark A and C correct (toggle two dots)
  5. Check "Tell participants how many correct answers to pick"
  6. Save the question, confirm it shows up with two "Correct" tags

Run:
    /home/vinay/Swaya.me/backend/.venv/bin/python3 scripts/verify_mcq_multi_builder.py
"""
import subprocess
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

sys.path.insert(0, '/home/vinay/Swaya.me/scripts')
from selenium_utils import inject_error_collectors, collect_js_errors  # noqa: E402

WEBDRIVER_URL = 'http://localhost:4444'
TARGET_BASE = 'https://test.swaya.me'
COOKIE_DOMAIN = 'test.swaya.me'
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


def main():
    token = subprocess.check_output(
        [PYTHON, '/home/vinay/Swaya.me/scripts/generate_selenium_token.py', 'meetnishant@gmail.com']
    ).decode().strip()
    print(f'{PASS} Token generated for meetnishant@gmail.com')

    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1440,1400')
    driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=options)
    driver.set_page_load_timeout(30)

    try:
        driver.get(TARGET_BASE)
        driver.add_cookie({
            'name': 'access_token', 'value': token, 'domain': COOKIE_DOMAIN,
            'path': '/', 'secure': True, 'httpOnly': True,
        })

        # ── 1. Create a new exam ────────────────────────────────────────────
        driver.get(f'{TARGET_BASE}/quiz/new?type=exam')
        time.sleep(2)
        inject_error_collectors(driver)

        title_input = wait_for(driver, By.ID, 'title', timeout=20) or wait_for(driver, By.CSS_SELECTOR, 'input[id*="title"]', timeout=10)
        if not check('Exam title input found', title_input is not None):
            raise SystemExit(1)
        title_input.clear()
        title_input.send_keys('mcq_multi builder verify')

        submit_btn = wait_for(driver, By.CSS_SELECTOR, 'button[type="submit"]', timeout=10)
        check('Create-exam submit button found', submit_btn is not None)
        submit_btn.click()

        WebDriverWait(driver, 20).until(EC.url_contains('/edit'))
        print(f'{INFO} Navigated to {driver.current_url}')
        time.sleep(2)

        # ── 2. Add a question, switch to mcq_multi ─────────────────────────
        add_btn = None
        for el in driver.find_elements(By.XPATH, "//button[contains(., 'Add') or contains(., 'question')]"):
            if el.is_displayed():
                add_btn = el
                break
        if add_btn:
            add_btn.click()
            time.sleep(1)

        multi_chip = None
        for el in driver.find_elements(By.CSS_SELECTOR, '.qb-type-chip'):
            if 'Multi-Select' in el.text:
                multi_chip = el
                break
        if not check('Multi-Select MCQ chip visible for exam type', multi_chip is not None):
            print(f'{INFO} Available chips: {[el.text for el in driver.find_elements(By.CSS_SELECTOR, ".qb-type-chip")]}')
            raise SystemExit(1)
        driver.execute_script('arguments[0].scrollIntoView(true); arguments[0].click();', multi_chip)
        time.sleep(1)
        check('Multi-Select MCQ chip now active', 'qb-type-chip--active' in multi_chip.get_attribute('class'))
        check('No option pre-marked correct right after switching to mcq_multi', len(driver.find_elements(By.CSS_SELECTOR, '.qb-option-card--correct')) == 0)

        # ── 3. Fill question text + 4 options ───────────────────────────────
        text_areas = driver.find_elements(By.CSS_SELECTOR, 'textarea, .rich-text-editor, [contenteditable="true"]')
        question_text_filled = False
        for ta in text_areas:
            if ta.is_displayed():
                try:
                    ta.click()
                    ta.send_keys('Which of these are prime numbers?')
                    question_text_filled = True
                    break
                except Exception:
                    continue
        check('Question text filled', question_text_filled)

        # Default mcq_multi option count is 2 (A, B) — click "Add option" twice for C, D
        for _ in range(2):
            add_option_btn = None
            for el in driver.find_elements(By.XPATH, "//button[contains(., 'Add option')]"):
                if el.is_displayed():
                    add_option_btn = el
                    break
            check('Add-option button found', add_option_btn is not None)
            if add_option_btn:
                driver.execute_script('arguments[0].click();', add_option_btn)
                time.sleep(0.4)

        inputs = driver.find_elements(By.CSS_SELECTOR, '.qb-opt-content input.ant-input')
        values = ['2', '4', '3', '6']
        for i, inp in enumerate(inputs[:4]):
            inp.clear()
            inp.send_keys(values[i])
        check('Filled 4 option text fields', len(inputs) >= 4)

        # ── 4. Toggle dots A and C (indices 0 and 2) ────────────────────────
        # Native .click() can be intercepted by hover-triggered antd Tooltips
        # sitting over adjacent buttons; dispatch via JS to click the actual element.
        def js_click(el):
            driver.execute_script('arguments[0].click();', el)

        dots = driver.find_elements(By.CSS_SELECTOR, '.qb-opt-dot')
        check('Found option dots', len(dots) >= 4)
        js_click(dots[0])
        time.sleep(0.4)
        dots = driver.find_elements(By.CSS_SELECTOR, '.qb-opt-dot')
        js_click(dots[2])
        time.sleep(0.4)

        correct_cards = driver.find_elements(By.CSS_SELECTOR, '.qb-option-card--correct')
        check('Exactly 2 options marked correct after toggling A and C', len(correct_cards) == 2)

        # Toggle A off and back on to confirm it's a real toggle, not a replace
        dots = driver.find_elements(By.CSS_SELECTOR, '.qb-opt-dot')
        js_click(dots[0])
        time.sleep(0.4)
        correct_cards_after_untoggle = driver.find_elements(By.CSS_SELECTOR, '.qb-option-card--correct')
        check('Untoggling A leaves exactly 1 correct (C)', len(correct_cards_after_untoggle) == 1)
        dots = driver.find_elements(By.CSS_SELECTOR, '.qb-opt-dot')
        js_click(dots[0])
        time.sleep(0.4)

        # ── 5. Check reveal_answer_count checkbox ───────────────────────────
        reveal_checkbox = None
        for label in driver.find_elements(By.XPATH, "//*[contains(text(),'correct answers to pick')]"):
            try:
                wrapper = label.find_element(By.XPATH, "./ancestor::label[contains(@class,'ant-checkbox-wrapper')]")
                reveal_checkbox = wrapper.find_element(By.CSS_SELECTOR, 'input')
                break
            except Exception:
                continue
        check('reveal_answer_count checkbox found', reveal_checkbox is not None)
        if reveal_checkbox:
            js_click(reveal_checkbox)
            time.sleep(0.3)
            check('reveal_answer_count checkbox now checked', reveal_checkbox.is_selected())

        # ── 6. Save the question ─────────────────────────────────────────────
        save_btn = None
        for el in driver.find_elements(By.XPATH, "//button[@type='submit']"):
            if el.is_displayed():
                save_btn = el
                break
        check('Save-question button found', save_btn is not None)
        if save_btn:
            driver.execute_script("arguments[0].scrollIntoView(true);", save_btn)
            js_click(save_btn)
        time.sleep(2)

        js_errors, failed_fetches = collect_js_errors(driver)
        check('No JS console errors', len(js_errors) == 0 and len(failed_fetches) == 0)
        if js_errors or failed_fetches:
            print(f'{INFO} JS errors: {js_errors}, failed fetches: {failed_fetches}')

        page_text = driver.find_element(By.TAG_NAME, 'body').text
        check('Question saved without visible error toast', 'error' not in page_text.lower()[:2000] or 'Error' not in page_text[:500])

        driver.save_screenshot('/tmp/claude-1005/-home-vinay-Swaya-me/e6372092-24c1-463a-96ef-7f243c36c5f0/scratchpad/mcq_multi_builder.png')
        print(f'{INFO} Screenshot saved')

        quiz_id = driver.current_url.rstrip('/').split('/')[-2]

    finally:
        driver.quit()

    import requests
    r = requests.get(f'{TARGET_BASE}/api/v1/quizzes/{quiz_id}', headers={'Authorization': f'Bearer {token}'})
    data = r.json()
    saved_questions = data.get('questions', [])
    check('Question persisted to backend', len(saved_questions) == 1)
    if saved_questions:
        q = saved_questions[0]
        check('question_type is mcq_multi', q.get('question_type') == 'mcq_multi')
        check('correct_answer_indices is [0, 2]', sorted(q.get('correct_answer_indices') or []) == [0, 2])
        check('reveal_answer_count is True', q.get('reveal_answer_count') is True)
        check('correct_answer_index is null', q.get('correct_answer_index') is None)
        print(f'{INFO} Saved question: {q}')

    print()
    if issues:
        print(f'{FAIL} {len(issues)} issue(s): {issues}')
        sys.exit(1)
    else:
        print(f'{PASS} All checks passed')


if __name__ == '__main__':
    main()

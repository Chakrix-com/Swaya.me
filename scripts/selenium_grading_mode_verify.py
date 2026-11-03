"""
Selenium verification for the grading-mode-selector feature (2026-08-09) on
test.swaya.me: the Grading Mode radio group + per-criterion scoring hints in
QuizBuilder's Grading tab, and the mode badge on CodingChallengeReview
(including the "Legacy" case for a submission with grading_mode_used=NULL).

Run:
    sudo docker exec selenium-arm python3 /scripts/selenium_grading_mode_verify.py

Watch live at: http://www.swaya.me:7900 (noVNC — no password)
"""
import subprocess
import sys
import time

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
TOKEN_SCRIPT = '/home/vinay/Swaya.me/scripts/generate_selenium_token.py'
PYTHON = '/home/vinay/Swaya.me/backend/.venv/bin/python3'

# From swayame_test: quiz 1279 / question 2255 is LIVE with a graded
# submission whose grading_mode_used=NULL (predates this feature) — the real
# "Legacy" badge case, not a synthetic one. But a live quiz's Grading form is
# intentionally read-only (disabled={isLiveMode} in GradingPanel.jsx) — found
# by clicking Deterministic and seeing nothing change, then noticing the
# "this challenge is live" banner in a screenshot, not a bug. Quiz 1280 /
# question 2256 is DRAFT, so it's used for the interactive radio-click check
# instead.
QUIZ_ID = 1279
QUESTION_ID = 2255
DRAFT_QUIZ_ID = 1280

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


def test_grading_panel(driver, quiz_id, interactive):
    print(f'\n{INFO} --- QuizBuilder Grading tab (quiz {quiz_id}, {"draft/interactive" if interactive else "live/read-only"}) ---')
    driver.get(f'{TARGET_BASE}/quiz/{quiz_id}/edit')
    time.sleep(3)
    inject_error_collectors(driver)

    # Land on the Grading tab — a nav item/tab labeled "Grading" (SetupPanel
    # uses stageView state, not a URL param, per QuizBuilder.jsx).
    grading_tab = wait_for(driver, By.XPATH, "//*[contains(text(),'Grading') and (self::div or self::span or self::button)]", timeout=15)
    check('Grading tab found', grading_tab is not None)
    if grading_tab:
        driver.execute_script("arguments[0].click();", grading_tab)
        time.sleep(2)

    # .text (not a raw XPath text()-node match) — "🧠 Grading Mode" is two
    # separate JSX text children (emoji literal + {t(...)} interpolation),
    # and XPath's contains(text(),...) only matches a single text node, not
    # concatenated content — a real gotcha hit while writing this check, not
    # a product bug (confirmed via a direct DOM dump before "fixing" this).
    section_titles = [el.text for el in driver.find_elements(By.CLASS_NAME, 'gp-section-title')]
    check(f'Grading Mode section renders (sections found: {section_titles})',
          any('Grading Mode' in t for t in section_titles))

    radio_buttons = driver.find_elements(By.CSS_SELECTOR, '.gp-section .ant-radio-button-wrapper')
    check('Grading mode radio buttons present (3 options)', len(radio_buttons) >= 3)

    hybrid_selected = driver.find_elements(By.CSS_SELECTOR, '.ant-radio-button-wrapper-checked')
    check('A grading mode is selected by default', len(hybrid_selected) > 0)

    scoring_hints = driver.find_elements(By.CLASS_NAME, 'gp-scoring-hint')
    check(f'Per-criterion scoring hints render ({len(scoring_hints)} found)', len(scoring_hints) >= 4)
    if scoring_hints:
        print(f'{INFO} Sample hint text: "{scoring_hints[0].text}"')

    # Click "Deterministic" and confirm the hints actually change (visible cue
    # requirement from the plan's §6 gap fix). Only meaningful on a DRAFT
    # quiz — GradingPanel's <Form disabled={isLiveMode}> intentionally makes
    # every control read-only on a live quiz, confirmed by first trying this
    # against a live quiz and seeing nothing change (not a bug, the "this
    # challenge is live" banner explains it) before switching to a draft one.
    if interactive:
        deterministic_btn = None
        for rb in radio_buttons:
            if 'Deterministic' in rb.text:
                deterministic_btn = rb
                break
        check('Deterministic option clickable', deterministic_btn is not None)
        if deterministic_btn:
            before_texts = {h.text for h in driver.find_elements(By.CLASS_NAME, 'gp-scoring-hint')}
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", deterministic_btn)
            time.sleep(0.5)
            deterministic_btn.click()  # native click — a JS-injected click on
            # this element didn't reliably fire antd's onChange in testing.
            time.sleep(2)
            after_texts = {h.text for h in driver.find_elements(By.CLASS_NAME, 'gp-scoring-hint')}
            check('Scoring hints change when Deterministic mode is selected', before_texts != after_texts)
            print(f'{INFO} Hints after selecting Deterministic: {sorted(after_texts)}')

    driver.save_screenshot(f'/tmp/grading_mode_panel_{quiz_id}.png')
    collect_js_errors(driver, 'GradingPanel')


def test_review_badge(driver):
    print(f'\n{INFO} --- CodingChallengeReview mode badge (question {QUESTION_ID}) ---')
    driver.get(f'{TARGET_BASE}/quiz/coding-challenge-review/{QUESTION_ID}')
    time.sleep(3)
    inject_error_collectors(driver)

    # Expand the Graded row — the "+" row-expand icon, not the row itself
    # (a `<tr>` click doesn't open the detail panel in this antd Table).
    expand_btn = wait_for(driver, By.CSS_SELECTOR, '.ant-table-row-expand-icon', timeout=15)
    check('Candidate row expand control found', expand_btn is not None)
    if expand_btn:
        driver.execute_script("arguments[0].click();", expand_btn)
        time.sleep(2)

    tag_texts = [t.text for t in driver.find_elements(By.CLASS_NAME, 'ant-tag')]
    check(f'Score Breakdown section renders (tags found: {tag_texts})', 'Platform default' in tag_texts)

    # This specific submission (id=1) has grading_mode_used=NULL in the DB —
    # must show the Legacy badge, not a blank or misleading default.
    check('Legacy badge shown for grading_mode_used=NULL submission', 'Legacy' in tag_texts)

    driver.save_screenshot('/tmp/grading_mode_review_badge.png')
    collect_js_errors(driver, 'CodingChallengeReview')


def main():
    import os
    token = os.environ.get('SWAYA_TOKEN', '').strip()
    if not token:
        print(f'{INFO} Generating JWT token...')
        try:
            token = subprocess.check_output([PYTHON, TOKEN_SCRIPT]).decode().strip()
        except Exception as e:
            print(f'{FAIL} Token generation failed: {e}')
            sys.exit(1)
    print(f'{PASS} Token ready ({token[:30]}...)')

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

        test_grading_panel(driver, QUIZ_ID, interactive=False)
        test_grading_panel(driver, DRAFT_QUIZ_ID, interactive=True)
        test_review_badge(driver)

        print(f'\n{"="*60}')
        if issues:
            print(f'{FAIL} {len(issues)} issue(s): {issues}')
            sys.exit(1)
        else:
            print(f'{PASS} All checks passed')
    finally:
        driver.quit()


if __name__ == '__main__':
    main()

"""
Full real-browser reproduction: log in as meetnishant@gmail.com, open quiz 279
edit page, unpublish if needed, run the AI-generate flow using the uploaded
Scrum Master Hiring Assessment.docx as the prompt file, and try to add the
generated questions to the quiz. Captures screenshots + JS errors + failed
fetches at each step so we can see exactly where/how it breaks.

Run:
    sudo docker exec selenium-arm python3 /scripts/repro_quiz279_ai_flow.py

Watch live at: http://www.swaya.me:7900 (noVNC — no password)
"""
import subprocess
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

sys.path.insert(0, '/scripts')
from selenium_utils import inject_error_collectors, collect_js_errors  # noqa: E402

WEBDRIVER_URL = 'http://localhost:4444'
TARGET_BASE = 'https://test.swaya.me'
COOKIE_DOMAIN = 'test.swaya.me'
DOCX_PATH = '/scripts/scrum_master_assessment.docx'

PASS = '\033[92m PASS\033[0m'
FAIL = '\033[91m FAIL\033[0m'
INFO = '\033[94m INFO\033[0m'
WARN = '\033[93m WARN\033[0m'

shot_n = [0]


def shot(driver, name):
    shot_n[0] += 1
    path = f'/tmp/q279_{shot_n[0]:02d}_{name}.png'
    driver.save_screenshot(path)
    print(f'{INFO} screenshot -> {path}')


def wait_for(driver, by, value, timeout=15, visible=True):
    try:
        cond = EC.visibility_of_element_located((by, value)) if visible else EC.presence_of_element_located((by, value))
        return WebDriverWait(driver, timeout).until(cond)
    except TimeoutException:
        return None


def main():
    import os
    token = os.environ.get('SWAYA_TOKEN', '').strip()
    if not token:
        print(f'{FAIL} No SWAYA_TOKEN provided')
        sys.exit(1)
    print(f'{PASS} Token ready ({token[:30]}...)')

    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1440,1000')
    driver = webdriver.Remote(command_executor=WEBDRIVER_URL, options=options)
    driver.set_page_load_timeout(30)

    try:
        driver.get(TARGET_BASE)
        driver.add_cookie({
            'name': 'access_token', 'value': token, 'domain': COOKIE_DOMAIN,
            'path': '/', 'secure': True, 'httpOnly': True,
        })
        print(f'{PASS} Cookie injected for {COOKIE_DOMAIN} (logged in as meetnishant@gmail.com)')

        driver.get(f'{TARGET_BASE}/quiz/279/edit')
        time.sleep(4)
        inject_error_collectors(driver)
        shot(driver, 'loaded')

        # Step 1: unpublish if currently live
        unpub_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Unpublish Quiz')]")
        if unpub_btns and unpub_btns[0].is_displayed():
            print(f'{INFO} Quiz is published — clicking Unpublish Quiz')
            driver.execute_script("arguments[0].click();", unpub_btns[0])
            time.sleep(2)
            shot(driver, 'after_unpublish')
        else:
            print(f'{INFO} Quiz already in draft (no Unpublish button visible)')

        # Step 2: open the AI generate modal
        ai_btn = wait_for(driver, By.XPATH, "//button[contains(., 'Generate with AI')]", timeout=10)
        if ai_btn is None:
            print(f'{FAIL} "Generate with AI" button not found even after unpublish')
            collect_js_errors(driver, 'no-ai-button')
            return
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", ai_btn)
        driver.execute_script("arguments[0].click();", ai_btn)
        time.sleep(1)
        modal = wait_for(driver, By.CLASS_NAME, 'ant-modal-content', timeout=10)
        if modal is None:
            print(f'{FAIL} AI modal did not open')
            collect_js_errors(driver, 'modal-open')
            return
        print(f'{PASS} AI generate modal opened')
        shot(driver, 'modal_open')

        # Step 3: switch to "Upload file" tab
        file_tab = wait_for(driver, By.XPATH, "//div[contains(@class,'ant-segmented-item-label')][contains(., 'Upload file')]", timeout=10)
        if file_tab is None:
            print(f'{FAIL} "Upload file" tab not found')
            collect_js_errors(driver, 'file-tab')
            return
        driver.execute_script("arguments[0].click();", file_tab)
        time.sleep(1)
        print(f'{PASS} Switched to Upload file tab')

        # Step 4: upload the docx via the hidden file input
        file_input = wait_for(driver, By.CSS_SELECTOR, "input[type=file]", timeout=10, visible=False)
        if file_input is None:
            print(f'{FAIL} File input not found')
            collect_js_errors(driver, 'file-input')
            return
        file_input.send_keys(DOCX_PATH)
        print(f'{INFO} File sent, waiting for extraction...')

        # Wait for either extracted text box or an error alert
        extracted = None
        extract_err = None
        for _ in range(30):
            time.sleep(1)
            extracted = driver.find_elements(By.CSS_SELECTOR, ".ant-alert-error")
            if extracted:
                extract_err = extracted[0].text
                break
            textareas = driver.find_elements(By.CSS_SELECTOR, "textarea")
            if any(t.get_attribute('value') and len(t.get_attribute('value')) > 100 for t in textareas):
                break
        shot(driver, 'after_extract')
        if extract_err:
            print(f'{FAIL} Extraction failed: {extract_err}')
            collect_js_errors(driver, 'extract-error')
            return
        print(f'{PASS} Text extracted from docx')

        # Step 5: click Generate
        gen_btn = wait_for(driver, By.XPATH, "//button[.//span[text()='Generate'] or contains(., 'Generate') and not(contains(., 'Generate with AI'))]", timeout=10)
        # Fallback: find primary button in modal footer area with text "Generate"
        if gen_btn is None:
            btns = driver.find_elements(By.XPATH, "//div[contains(@class,'ant-modal')]//button")
            for b in btns:
                if b.text.strip() == 'Generate':
                    gen_btn = b
                    break
        if gen_btn is None:
            print(f'{FAIL} Generate button not found')
            collect_js_errors(driver, 'generate-button')
            return
        driver.execute_script("arguments[0].click();", gen_btn)
        print(f'{INFO} Clicked Generate — waiting for streaming to finish...')

        # Wait for stream to complete: "Add to Quiz" button becomes non-disabled, or an error appears
        add_btn = None
        gen_error = None
        for _ in range(90):
            time.sleep(1)
            errs = driver.find_elements(By.CSS_SELECTOR, ".ant-alert-error")
            if errs:
                gen_error = errs[0].text
                break
            candidates = driver.find_elements(By.XPATH, "//button[contains(., 'Add') and contains(., 'question')]")
            if candidates and candidates[0].is_enabled():
                add_btn = candidates[0]
                break
        shot(driver, 'after_generate')
        if gen_error:
            print(f'{FAIL} Generation error shown: {gen_error}')
            collect_js_errors(driver, 'generate-error')
            return
        if add_btn is None:
            print(f'{FAIL} Never became ready to add questions (timeout)')
            collect_js_errors(driver, 'generate-timeout')
            return
        print(f'{PASS} Questions generated, preview ready: "{add_btn.text}"')

        # Step 6: click Add to Quiz
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", add_btn)
        driver.execute_script("arguments[0].click();", add_btn)
        print(f'{INFO} Clicked Add — waiting for result...')
        time.sleep(4)
        shot(driver, 'after_add')

        # Check for success message, error message, or crash
        success = driver.find_elements(By.CSS_SELECTOR, ".ant-message-success")
        error_msgs = driver.find_elements(By.CSS_SELECTOR, ".ant-message-error, .ant-message-notice-error")
        error_boundary = driver.find_elements(By.XPATH, "//*[contains(text(),'Something went wrong') or contains(text(),'unexpected error')]")

        if success:
            print(f'{PASS} Success message shown: {[s.text for s in success]}')
        if error_msgs:
            print(f'{FAIL} Error message shown: {[e.text for e in error_msgs]}')
        if error_boundary:
            print(f'{FAIL} Error boundary / crash screen text found: {[e.text for e in error_boundary]}')
        if not success and not error_msgs and not error_boundary:
            print(f'{WARN} No success/error message detected — inspect screenshot manually')

        collect_js_errors(driver, 'final')
        page_source_snippet = driver.find_element(By.TAG_NAME, 'body').text[:300]
        print(f'{INFO} Body text snippet: {page_source_snippet}')

    finally:
        driver.quit()


if __name__ == '__main__':
    main()
